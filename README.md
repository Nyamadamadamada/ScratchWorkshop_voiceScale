# こえで つくる がっき

声を録音して、その高さを測り、ドレミファソラシドの8音のWAVに変換する。
Scratch の「音をアップロード」に読ませて、自分の声を楽器にする。

https://nyamadamadamada.github.io/ScratchWorkshop_voiceScale/

ブラウザだけで完結する静的サイト。サーバー処理はなく、録音した声は外に出ない。
配信する JavaScript に外部依存はない。

```
docs/               GitHub Pages で配信する一式
src/voice_scale/    Python 版。見本音源づくりと検証に使う
tests/              テストの読みかたは tests/README.md
```

## 動かす

```sh
uv sync
uv run python -m http.server -d docs 8765
```

`http://localhost:8765/` を開く。`localhost` はセキュアコンテキスト扱いなのでマイクが使える。

## 確認する

```sh
uv run ruff check --fix . && uv run ruff format .
uv run pytest

npm install
npm test                      # 実ブラウザで通し確認（要 Google Chrome、先に上のサーバーを立てる）
node tests/e2e/shot.mjs /tmp/shot   # 画面のスクリーンショットを撮る
```

見本音源をつくるとき。

```sh
uv run voice-scale info  素材/にゃー.mp3            # 声の高さと判定を表示
uv run voice-scale build 素材/にゃー.mp3 -o 見本/   # 8音のWAVを書き出す
```

## デプロイ

`main` に push すれば反映される。GitHub Pages の Source は `main` ブランチの `/docs`。

```sh
BASE_URL=https://nyamadamadamada.github.io/ScratchWorkshop_voiceScale/ npm test
```

公開後はこれで本番URLを確認する。
