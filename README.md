# 声から音階を作ろう

声を録音して、その高さを測り、ドレミファソラシドの8音のWAVに変換する。
Scratch の「音をアップロード」に読ませて、自分の声を楽器にする。

https://nyamadamadamada.github.io/ScratchWorkshop_voiceScale/

ブラウザだけで完結する静的サイト。サーバー処理はなく、録音した声は外に出ない。
配信する JavaScript に外部依存はない。

## 組み立てかた

**音をつくるのは JavaScript だけ。Python は同じ処理を持たない。**
役割をこう分けてある。

| | 受け持ち |
| --- | --- |
| Node | 動かす。アプリ本体、見本音源づくり、実ブラウザでの通し確認 |
| Python | 測る。できあがった WAV を読んで、狙いどおりか確かめる |

```
docs/               GitHub Pages で配信する一式
  index.html        入り口。読み込むスクリプトは app.js だけ
  app.js            画面の配線
  sound/            音をつくる（純粋な関数）
  save/             ZIP にまとめて保存する
  device/           マイクとスピーカー（ブラウザの資源を持つのでクラス）
tools/generate.mjs  実ブラウザで8音をつくる。見本づくりとテストが使う
src/voice_scale/    できた WAV を測る
tests/              テストの読みかたは tests/README.md
```

クラスは後始末や状態を抱えるものだけ。`Recorder` `Player` `SoundSet` の3つしかない。

## 動かす

```sh
uv sync
uv run python -m http.server -d docs 8760
```

`http://localhost:8760/` を開く。`localhost` はセキュアコンテキスト扱いなのでマイクが使える。

## 確認する

```sh
uv run ruff check --fix . && uv run ruff format .
uv run pytest            # ブラウザに音をつくらせて、その WAV を測る
npm test                 # 画面1から画面2まで実ブラウザで通す（要 Chrome）
npm run shot -- /tmp/x   # 画面のスクリーンショットを撮る
```

`uv run pytest` と `npm test` は Chrome を使う。サーバーは pytest 側が自分で立てる。

## 見本音源をつくる

```sh
npm run samples -- --file ../素材/にゃー.mp3 --out ../見本/にゃー
uv run voice-scale check ../見本/にゃー
```

`generate.mjs` は実ブラウザで `docs/sound/` をそのまま動かす。
つまり当日子どもが動かすコードと同じものから見本ができる。

## デプロイ

`main` に push すれば反映される。GitHub Pages の Source は `main` ブランチの `/docs`。
