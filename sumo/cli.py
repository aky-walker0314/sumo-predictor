"""使い方: python -m sumo.cli update   （データ取得 → 学習 → 予想 → サイト生成）
         python -m sumo.cli build    （サイト生成だけ。データは取得しない）
"""
from __future__ import annotations

import argparse
import json

from . import dataset, features, model, predict, site


def _prepare(fetch: bool):
    if fetch:
        dataset.build()
    bouts, names = dataset.load()
    table, state = features.build_training(bouts)
    return bouts, names, table, state


def update() -> None:
    bouts, names, table, state = _prepare(fetch=True)
    completed = sorted(b for b, g in bouts.groupby("basho") if g["day"].max() == 15)

    ev = model.evaluate(table, completed[-6:], kinds=("logreg",))
    site.METRICS.write_text(json.dumps(ev, ensure_ascii=False, indent=1))
    print(f"検証 {ev['test_bashos'][0]}〜{ev['test_bashos'][-1]}: 的中率 {ev['logreg']['accuracy']:.3f}")

    latest = max(bouts["basho"])
    if latest in completed:
        # 場所が終わっていて予想が無い（＝公開前の場所）なら事後検証を作る
        if predict.load(latest) is None:
            predict.backtest(latest, table, names)
            print(f"{latest}: 事後検証を作成")
    else:
        day = predict.live(latest, bouts, state, model.fit(table), names)
        print(f"{latest}: {day}日目を予想" if day else f"{latest}: 新しい予想なし")

    # 初日の取組が発表された新しい場所（まだ bouts に1番も無い）
    for basho in dataset.api.basho_ids()[-2:]:
        if basho > latest:
            day = predict.live(basho, bouts, state, model.fit(table), names)
            if day:
                print(f"{basho}: {day}日目を予想")

    site.build(bouts, state, names)
    print(f"サイトを生成: {site.OUT}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["update", "build"])
    args = p.parse_args()
    if args.command == "update":
        update()
    else:
        bouts, names, _, state = _prepare(fetch=False)
        site.build(bouts, state, names)


if __name__ == "__main__":
    main()
