"""予想データから静的サイト（site/）を生成する。"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from . import api, predict
from .dataset import rank_jp
from .features import State
from .kimarite import kimarite_jp

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
METRICS = ROOT / "data" / "metrics.json"

_MONTH = {"01": "一月場所（初場所）", "03": "三月場所（春場所）", "05": "五月場所（夏場所）",
          "07": "七月場所（名古屋場所）", "09": "九月場所（秋場所）", "11": "十一月場所（九州場所）"}
_DAY = ["", "初日", "二日目", "三日目", "四日目", "五日目", "六日目", "七日目", "中日",
        "九日目", "十日目", "十一日目", "十二日目", "十三日目", "十四日目", "千秋楽"]


def basho_name(basho: str, short: bool = False) -> str:
    y, m = int(basho[:4]), basho[4:]
    era = f"令和{y - 2018}年" if y >= 2019 else f"{y}年"
    name = _MONTH[m]
    return f"{era}{name.split('（')[0] if short else name}"


def _results(bouts: pd.DataFrame, basho: str) -> dict:
    b = bouts[bouts["basho"] == basho]
    return {(int(r.day), int(r.a_id), int(r.b_id)): r for r in b.itertuples()}


def _basho_view(pred: dict, bouts: pd.DataFrame) -> dict:
    res = _results(bouts, pred["basho"])
    days, hit_total, n_total = [], 0, 0
    for d in sorted(pred["days"], key=int):
        rows, hits, n = [], 0, 0
        for e in pred["days"][d]["bouts"]:
            r = res.get((int(d), min(e["east_id"], e["west_id"]), max(e["east_id"], e["west_id"])))
            pick_east = e["p_east"] >= 0.5
            row = dict(e, pick_east=pick_east, p_west=1 - e["p_east"], winner=None, hit=None, kimarite="", fusen=False)
            if r is not None:
                row["winner"] = "east" if r.winner_id == e["east_id"] else "west"
                row["kimarite"] = kimarite_jp(r.kimarite)
                row["fusen"] = bool(r.fusen)
                if not row["fusen"]:
                    row["hit"] = (row["winner"] == "east") == pick_east
                    hits += row["hit"]
                    n += 1
            rows.append(row)
        hit_total += hits
        n_total += n
        days.append({"day": int(d), "label": _DAY[int(d)], "bouts": rows, "hits": hits, "n": n,
                     "predicted_at": pred["days"][d].get("predicted_at", "")})
    return {"basho": pred["basho"], "name": basho_name(pred["basho"]), "mode": pred["mode"], "days": days,
            "hits": hit_total, "n": n_total}


def _ranking(state: State, names: dict, basho: str, top: int = 20) -> list[dict]:
    rows = []
    bz = api.banzuke(basho, "Makuuchi")
    for r in (bz.get("east") or []) + (bz.get("west") or []):
        rows.append((r["rikishiID"], r["rank"], r.get("wins", 0), r.get("losses", 0), r.get("absences", 0)))
    rows.sort(key=lambda x: -state.elo[x[0]])
    out = []
    for i, (rid, rank, w, l, a) in enumerate(rows[:top], 1):
        out.append({"pos": i, "name": names.get(rid, {}).get("jp", str(rid)), "rank": rank_jp(rank),
                    "elo": round(state.elo[rid]), "record": "全休" if a >= 15 else f"{w}勝{l}敗" + (f"{a}休" if a else "")})
    return out


def build(bouts: pd.DataFrame, state: State, names: dict) -> None:
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    tpl = env.get_template("basho.html")
    metrics = json.loads(METRICS.read_text()) if METRICS.exists() else None
    preds = sorted(predict.PRED_DIR.glob("*.json"))
    views = [_basho_view(json.loads(p.read_text()), bouts) for p in preds]
    latest = max(bouts["basho"])
    ranking = _ranking(state, names, latest)
    archive = [{"basho": v["basho"], "name": v["name"], "mode": v["mode"], "hits": v["hits"], "n": v["n"]}
               for v in reversed(views)]
    generated = datetime.now(predict.JST).strftime("%Y-%m-%d %H:%M")

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "basho").mkdir(parents=True)
    for v in views:
        ctx = dict(view=v, metrics=metrics, ranking=None, archive=archive, generated=generated, root="../")
        (OUT / "basho" / f"{v['basho']}.html").write_text(tpl.render(**ctx))
    if views:
        ctx = dict(view=views[-1], metrics=metrics, ranking=ranking, archive=archive, generated=generated, root="",
                   ranking_basho=basho_name(latest, short=True))
        (OUT / "index.html").write_text(tpl.render(**ctx))
    shutil.copy(ROOT / "templates" / "style.css", OUT / "style.css")
    (OUT / ".nojekyll").write_text("")
