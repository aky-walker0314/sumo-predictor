# 大相撲AI勝敗予想

2000年以降の幕内・十両の全取組（約8万番）で学習したAIが、幕内の取組の勝敗を予想し、静的サイトとして公開します。

- データ: [sumo-api.com](https://sumo-api.com)（番付・星取り・取組）
- モデル: Eloレーティング＋番付差・今場所の星・7勝7敗の星勘定・対戦成績・直近の調子などを特徴量にしたロジスティック回帰
- 精度: 直近6場所（2972番）で的中率 58.6%（番付上位が勝つ: 54.5%、Eloのみ: 57.8%）
- 公開: GitHub Pages（GitHub Actions で毎日自動更新）

## ローカルで動かす

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m sumo.cli update      # データ取得 → 学習 → 予想 → site/ を生成
python3 -m http.server 8765 --directory site
```

`update` は次のことをします。

1. 2000年以降の番付・星取りを取得（終わった場所は `data/raw/` にキャッシュ）
2. 直近6場所で精度を検証して `data/metrics.json` に保存
3. 場所中なら、翌日の取組が発表されていれば予想して `data/predictions/{場所ID}.json` に保存
   - 一度保存した日の予想は上書きしません（結果を見てから予想を直せないようにするため）
4. 公開前に終わった場所は「事後検証」（その場所より前のデータだけで学習したモデルで予想）を作成
5. `site/` に静的サイトを生成

## 構成

| ファイル | 役割 |
| --- | --- |
| `sumo/api.py` | sumo-api.com からの取得とキャッシュ |
| `sumo/dataset.py` | 星取りを取組単位の表（`data/bouts.csv`）に変換 |
| `sumo/features.py` | 取組を時系列に流して、その時点までの情報だけで特徴量を作る（Elo など） |
| `sumo/model.py` | 学習・評価 |
| `sumo/predict.py` | 予想の作成と保存 |
| `sumo/site.py`, `templates/` | サイト生成 |
| `.github/workflows/update.yml` | 毎日 19:30 / 8:00 JST に更新して GitHub Pages に公開 |

## 注意

予想は娯楽目的です。日本相撲協会とは関係ありません。
