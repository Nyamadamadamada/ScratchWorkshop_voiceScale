# 声から音階を作ろう

声を録音して、その高さを測り、ドレミファソラシドの8音のWAVに変換する。

https://nyamadamadamada.github.io/ScratchWorkshop_voiceScale/

ブラウザだけで完結する静的サイト。サーバー処理はなく、録音した声は外に出ない。

```
docs/               GitHub Pages で配信する一式
src/voice_scale/    Python 版。見本音源づくりとローカル検証に使う
tests/              テスト
```

`docs/` と `src/voice_scale/` は1対1で対応する。`pitch` `check` `audio` `scale` `wav`
は同じ名前のファイルに同じ処理が入っていて、同じ値を返す。ずれていないことは
`tests/test_parity.py` で確かめる。

純粋な計算は関数にする。クラスは後始末が要るものだけで、`Recorder` `Player` `SoundSet`
の3つしかない。

## 環境構築

```sh
uv sync
uv run python -m http.server -d docs 8760
```

`http://localhost:8760/` を開く。`localhost` はセキュアコンテキスト扱いなのでマイクが使える。

## リンター/テスト

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
