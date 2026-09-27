"""sumo-api.com から番付・取組を取得する（完了済みの場所はローカルにキャッシュ）。"""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import requests

BASE = "https://sumo-api.com/api"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
DIVISIONS = ("Makuuchi", "Juryo")
BASHO_MONTHS = (1, 3, 5, 7, 9, 11)

_session = requests.Session()
_session.headers["User-Agent"] = "sumo-predictor (hobby project)"


def _get(path: str) -> dict:
    for attempt in range(4):
        try:
            r = _session.get(f"{BASE}{path}", timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def basho_ids(start_year: int = 2000, until: date | None = None) -> list[str]:
    """start_year から until（既定: 今日）までの場所ID（YYYYMM）を古い順に返す。"""
    until = until or date.today()
    ids = []
    for y in range(start_year, until.year + 1):
        for m in BASHO_MONTHS:
            if (y, m) <= (until.year, until.month):
                ids.append(f"{y}{m:02d}")
    return ids


def _is_complete(banzuke: dict) -> bool:
    rows = (banzuke.get("east") or []) + (banzuke.get("west") or [])
    return bool(rows) and all(len(r.get("record") or []) >= 15 for r in rows)


def banzuke(basho_id: str, division: str, refresh: bool = False) -> dict:
    """番付（各力士の15日分の星取り付き）。千秋楽まで終わった場所だけキャッシュする。"""
    path = CACHE_DIR / f"banzuke_{basho_id}_{division}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    data = _get(f"/basho/{basho_id}/banzuke/{division}")
    if _is_complete(data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False))
    return data


def torikumi(basho_id: str, division: str, day: int) -> dict:
    """指定日の取組（未決着なら winnerId が空）。常に最新を取得する。"""
    return _get(f"/basho/{basho_id}/torikumi/{division}/{day}")
