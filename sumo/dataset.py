"""番付の星取りから取組単位の表（bouts.csv）を作る。"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import api

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BOUTS_CSV = DATA_DIR / "bouts.csv"
RIKISHI_CSV = DATA_DIR / "rikishi.csv"

_RANK_RE = re.compile(r"^(Yokozuna|Ozeki|Sekiwake|Komusubi|Maegashira|Juryo|Makushita)\s*(\d+)?\s*(East|West)?")
_TITLE_BASE = {"Yokozuna": 0, "Ozeki": 1, "Sekiwake": 2, "Komusubi": 3, "Maegashira": 3, "Juryo": 20, "Makushita": 34}
_TITLE_JP = {"Yokozuna": "横綱", "Ozeki": "大関", "Sekiwake": "関脇", "Komusubi": "小結",
             "Maegashira": "前頭", "Juryo": "十両", "Makushita": "幕下"}


def rank_ordinal(rank: str | None) -> float | None:
    """番付を数値化（小さいほど上位）。横綱=0, 大関=1, 関脇=2, 小結=3, 前頭n=3+n, 十両n=20+n。"""
    if not isinstance(rank, str) or not rank:
        return None
    m = _RANK_RE.match(rank)
    if not m:
        return None
    title, num, side = m.groups()
    value = float(_TITLE_BASE[title])
    if title in ("Maegashira", "Juryo", "Makushita"):
        value += int(num or 1)
    return value + (0.25 if side == "West" else 0.0)


def rank_jp(rank: str | None) -> str:
    if not isinstance(rank, str) or not rank:
        return ""
    m = _RANK_RE.match(rank)
    if not m:
        return rank
    title, num, side = m.groups()
    side_jp = {"East": "東", "West": "西"}.get(side or "", "")
    num_jp = num if title in ("Maegashira", "Juryo", "Makushita") else ""
    return f"{side_jp}{_TITLE_JP[title]}{num_jp}"


def shikona_jp(full: str | None) -> str:
    """'大の里　泰輝' → '大の里'、'一意(かずま)' → '一意'。"""
    if not full:
        return ""
    return re.split(r"[\s　(（]", full.strip())[0]


def build(start_year: int = 2000, refresh_recent: int = 2) -> pd.DataFrame:
    ids = api.basho_ids(start_year)
    recent = set(ids[-refresh_recent:])
    rows: dict[tuple, dict] = {}
    names: dict[int, tuple[str, str]] = {}
    for basho_id in ids:
        ranks: dict[int, str] = {}
        entries = []
        for div in api.DIVISIONS:
            bz = api.banzuke(basho_id, div, refresh=basho_id in recent)
            for r in (bz.get("east") or []) + (bz.get("west") or []):
                rid = r["rikishiID"]
                ranks[rid] = r["rank"]
                names[rid] = (shikona_jp(r.get("shikonaJp")) or r.get("shikonaEn", ""), r.get("shikonaEn", ""))
                entries.append((div, r))
        if not entries:
            continue  # 中止場所（2011年3月、2020年5月）
        print(f"{basho_id}: {len(entries)} rikishi")
        for div, r in entries:
            rid = r["rikishiID"]
            for i, x in enumerate(r.get("record") or []):
                result = x.get("result", "")
                if result not in ("win", "loss", "fusen win", "fusen loss"):
                    continue
                opp = x.get("opponentID")
                if not opp:
                    continue
                day = i + 1
                a, b = sorted((rid, opp))
                key = (basho_id, day, a, b)
                if key in rows:
                    continue
                won = result.endswith("win")
                rows[key] = {
                    "basho": basho_id, "day": day, "a_id": a, "b_id": b,
                    "a_rank": ranks.get(a), "b_rank": ranks.get(b),
                    "winner_id": rid if won else opp,
                    "fusen": result.startswith("fusen"),
                    "kimarite": x.get("kimarite", ""),
                }
                if opp not in names and x.get("opponentShikonaEn"):
                    names[opp] = (shikona_jp(x.get("opponentShikonaJp")) or x["opponentShikonaEn"], x["opponentShikonaEn"])
    df = pd.DataFrame(rows.values()).sort_values(["basho", "day", "a_id"]).reset_index(drop=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(BOUTS_CSV, index=False)
    pd.DataFrame([{"id": k, "name_jp": v[0], "name_en": v[1]} for k, v in names.items()]).to_csv(RIKISHI_CSV, index=False)
    return df


def load() -> tuple[pd.DataFrame, dict[int, dict]]:
    bouts = pd.read_csv(BOUTS_CSV, dtype={"basho": str})
    rik = pd.read_csv(RIKISHI_CSV)
    names = {int(r.id): {"jp": r.name_jp, "en": r.name_en} for r in rik.itertuples()}
    return bouts, names
