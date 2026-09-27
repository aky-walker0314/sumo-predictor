"""幕内の取組予想を作り data/predictions/{場所ID}.json に保存する。

予想は一度保存したら上書きしない（結果が出た後に予想を書き換えられないようにするため）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import api, model
from .dataset import rank_jp
from .features import ANTISYMMETRIC, FEATURES, State

PRED_DIR = Path(__file__).resolve().parent.parent / "data" / "predictions"
JST = timezone(timedelta(hours=9))


def load(basho: str) -> dict | None:
    path = PRED_DIR / f"{basho}.json"
    return json.loads(path.read_text()) if path.exists() else None


def save(pred: dict) -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    (PRED_DIR / f"{pred['basho']}.json").write_text(json.dumps(pred, ensure_ascii=False, indent=1))


def _now() -> str:
    return datetime.now(JST).isoformat(timespec="minutes")


def _entries(matches: list[dict], feats: list[dict], m, names: dict) -> list[dict]:
    X = pd.DataFrame(feats)[FEATURES]
    p = model.predict(m, X)
    out = []
    for t, pe in zip(matches, p):
        out.append({
            "east_id": t["eastId"], "west_id": t["westId"],
            "east": names.get(t["eastId"], {}).get("jp") or t.get("eastShikona", ""),
            "west": names.get(t["westId"], {}).get("jp") or t.get("westShikona", ""),
            "east_rank": rank_jp(t.get("eastRank")), "west_rank": rank_jp(t.get("westRank")),
            "p_east": round(float(pe), 4),
        })
    return out


def live(basho: str, bouts: pd.DataFrame, state: State, m, names: dict) -> int | None:
    """次の日の取組が発表済みで未予想なら予想して保存する。予想した日を返す。"""
    done = bouts[bouts["basho"] == basho]["day"]
    day = int(done.max()) + 1 if len(done) else 1
    if day > 15:
        return None
    pred = load(basho) or {"basho": basho, "mode": "live", "days": {}}
    if str(day) in pred["days"]:
        return None
    matches = [t for t in (api.torikumi(basho, "Makuuchi", day).get("torikumi") or [])
               if t.get("eastId") and t.get("westId")]
    if not matches or any(t.get("winnerId") for t in matches):
        return None  # 未発表、またはすでに取組が始まっている
    feats = []
    for t in matches:
        f = state.features(t["eastId"], t["westId"], basho, day, t.get("eastRank"), t.get("westRank"))
        if f is None:
            return None
        feats.append(f)
    pred["days"][str(day)] = {"predicted_at": _now(), "bouts": _entries(matches, feats, m, names)}
    save(pred)
    return day


def backtest(basho: str, table: pd.DataFrame, names: dict) -> dict:
    """終わった場所を「その場所の前までのデータだけで学習したモデル」で事後検証する。"""
    m = model.fit(table[table["basho"] < basho])
    rows = table[table["basho"] == basho]
    lookup = {(int(r.day), int(r.a_id), int(r.b_id)): r for r in rows.itertuples()}
    pred = {"basho": basho, "mode": "backtest", "created_at": _now(), "days": {}}
    for day in range(1, 16):
        matches, feats = [], []
        for t in api.torikumi(basho, "Makuuchi", day).get("torikumi") or []:
            e, w = t.get("eastId"), t.get("westId")
            r = lookup.get((day, min(e or 0, w or 0), max(e or 0, w or 0)))
            if r is None:
                continue  # 不戦など
            f = {k: getattr(r, k) for k in FEATURES}
            if e != r.a_id:  # 表は id の小さい方が A なので東西に合わせて反転
                f = {k: (-v if k in ANTISYMMETRIC else v) for k, v in f.items()}
            matches.append(t)
            feats.append(f)
        if matches:
            pred["days"][str(day)] = {"bouts": _entries(matches, feats, m, names)}
    save(pred)
    return pred
