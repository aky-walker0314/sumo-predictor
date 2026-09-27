"""勝敗予測モデルの学習・評価。"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES, flip

TRAIN_FROM = "200401"  # 2000年からのElo立ち上がり期間は学習に使わない


def _augment(X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, np.ndarray]:
    return pd.concat([X, flip(X)], ignore_index=True), np.concatenate([y.values, 1 - y.values])


def make(kind: str = "gbm"):
    if kind == "logreg":
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
    return HistGradientBoostingClassifier(
        learning_rate=0.04, max_iter=400, max_leaf_nodes=15, min_samples_leaf=200,
        l2_regularization=1.0, random_state=0,
    )


def fit(train: pd.DataFrame, kind: str = "logreg"):
    train = train[train["basho"] >= TRAIN_FROM]
    X, y = _augment(train[FEATURES], train["y"])
    return make(kind).fit(X, y)


def predict(model, X: pd.DataFrame) -> np.ndarray:
    """A の勝率。A/B を入れ替えた予測と平均して左右対称にする。"""
    X = X[FEATURES]
    return 0.5 * (model.predict_proba(X)[:, 1] + 1 - model.predict_proba(flip(X))[:, 1])


def rank_baseline(X: pd.DataFrame) -> np.ndarray:
    """番付が上の力士が勝つ（同格なら Elo が上）。"""
    return np.where(X["rank_diff"] != 0, X["rank_diff"] > 0, X["elo_p"] > 0.5).astype(float)


def scores(y, p) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"accuracy": float(accuracy_score(y, p > 0.5)), "logloss": float(log_loss(y, p, labels=[0, 1])), "n": int(len(y))}


def evaluate(table: pd.DataFrame, test_bashos: list[str], kinds=("gbm", "logreg")) -> dict:
    """test_bashos より前だけで学習し、test_bashos で評価する（時系列ホールドアウト）。"""
    first = min(test_bashos)
    train, test = table[table["basho"] < first], table[table["basho"].isin(test_bashos)]
    result = {
        "test_bashos": test_bashos,
        "番付上位が勝つ": scores(test["y"], rank_baseline(test)),
        "Eloのみ": scores(test["y"], test["elo_p"]),
    }
    for kind in kinds:
        result[kind] = scores(test["y"], predict(fit(train, kind), test))
    return result
