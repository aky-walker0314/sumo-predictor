"""取組を時系列に流しながら「その取組の前の時点で分かっていた情報」だけで特徴量を作る。"""
from __future__ import annotations

import math
from collections import defaultdict, deque

import pandas as pd

from .dataset import rank_ordinal

ELO_START = 1500.0
FORM_WINDOW = 30

# A と B を入れ替えると符号が反転する特徴量（それ以外は入れ替えても値が同じ）
ANTISYMMETRIC = [
    "elo_diff", "rank_diff", "net_diff", "prev_wins_diff", "h2h_score",
    "form_diff", "exp_diff", "edge_diff", "kk_diff", "mk_diff",
]
SYMMETRIC = ["h2h_n", "day"]
FEATURES = ANTISYMMETRIC + SYMMETRIC


class State:
    def __init__(self) -> None:
        self.elo: dict[int, float] = defaultdict(lambda: ELO_START)
        self.n: dict[int, int] = defaultdict(int)
        self.recent: dict[int, deque] = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
        self.rec: dict[tuple[str, int], list[int]] = defaultdict(lambda: [0, 0])
        self.last_basho: dict[int, str] = {}
        self.prev_basho: dict[int, str] = {}
        self.h2h: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0, 0])

    # ---- 参照 ----
    def expected(self, a: int, b: int) -> float:
        return 1.0 / (1.0 + 10 ** ((self.elo[b] - self.elo[a]) / 400.0))

    def _prev_wins(self, rid: int, basho: str) -> float:
        prev = self.last_basho.get(rid)
        if prev == basho:
            prev = self.prev_basho.get(rid)
        if prev is None:
            return 7.5
        w, l = self.rec[(prev, rid)]
        return w * 15.0 / max(w + l, 1)  # 途中休場も15日換算

    def _form(self, rid: int) -> float:
        r = self.recent[rid]
        return (sum(r) + 5) / (len(r) + 10)

    def features(self, a: int, b: int, basho: str, day: int, rank_a: str | None, rank_b: str | None) -> dict | None:
        oa, ob = rank_ordinal(rank_a), rank_ordinal(rank_b)
        if oa is None or ob is None:
            return None
        wa, la = self.rec[(basho, a)]
        wb, lb = self.rec[(basho, b)]
        key = (min(a, b), max(a, b))
        h = self.h2h[key]
        ha, hb = (h[0], h[1]) if a < b else (h[1], h[0])
        edge = lambda w, l: 1.0 if (l == 7 and w <= 7) else 0.0  # あと1敗で負け越し
        return {
            "elo_diff": (self.elo[a] - self.elo[b]) / 100.0,
            "rank_diff": ob - oa,
            "net_diff": (wa - la) - (wb - lb),
            "prev_wins_diff": self._prev_wins(a, basho) - self._prev_wins(b, basho),
            "h2h_score": (ha - hb) / (ha + hb + 2),
            "form_diff": self._form(a) - self._form(b),
            "exp_diff": math.log1p(self.n[a]) - math.log1p(self.n[b]),
            "edge_diff": edge(wa, la) - edge(wb, lb),
            "kk_diff": float(wa >= 8) - float(wb >= 8),
            "mk_diff": float(la >= 8) - float(lb >= 8),
            "h2h_n": math.log1p(ha + hb),
            "day": float(day),
        }

    # ---- 更新 ----
    def _enter_basho(self, rid: int, basho: str) -> None:
        last = self.last_basho.get(rid)
        if last != basho:
            if last is not None:
                self.prev_basho[rid] = last
            self.last_basho[rid] = basho

    def update(self, a: int, b: int, winner: int, basho: str, fusen: bool) -> None:
        for rid in (a, b):
            self._enter_basho(rid, basho)
        loser = b if winner == a else a
        self.rec[(basho, winner)][0] += 1
        self.rec[(basho, loser)][1] += 1
        if fusen:
            return  # 不戦は実力の情報にならないので星数だけ数える
        exp_w = self.expected(winner, loser)
        for rid, score, exp in ((winner, 1.0, exp_w), (loser, 0.0, 1.0 - exp_w)):
            k = 32.0 if self.n[rid] < 50 else 16.0
            self.elo[rid] += k * (score - exp)
            self.n[rid] += 1
            self.recent[rid].append(score)
        key = (min(a, b), max(a, b))
        self.h2h[key][0 if winner == key[0] else 1] += 1


def build_training(bouts: pd.DataFrame) -> tuple[pd.DataFrame, State]:
    """全取組を時系列に処理し、学習用の特徴量表と最終状態を返す。"""
    state = State()
    out = []
    for (basho, day), g in bouts.groupby(["basho", "day"], sort=True):
        recs = g.to_dict("records")
        for r in recs:
            if r["fusen"]:
                continue
            f = state.features(r["a_id"], r["b_id"], basho, day, r["a_rank"], r["b_rank"])
            if f is None:
                continue
            f.update(basho=basho, a_id=r["a_id"], b_id=r["b_id"], y=int(r["winner_id"] == r["a_id"]),
                     elo_p=state.expected(r["a_id"], r["b_id"]))
            out.append(f)
        for r in recs:
            state.update(r["a_id"], r["b_id"], r["winner_id"], basho, bool(r["fusen"]))
    return pd.DataFrame(out), state


def flip(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    X[ANTISYMMETRIC] = -X[ANTISYMMETRIC]
    return X
