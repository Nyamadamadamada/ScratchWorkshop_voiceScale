"""できあがった音を測る。

音をつくるのは docs/ の JavaScript だけで、Python は同じ処理を持たない。
役割をこう分けてある。

    Node    動かす。アプリ本体、見本音源づくり、実ブラウザでの通し確認
    Python  測る。できた WAV を読んで、狙いどおりか確かめる

見本音源は `node tools/generate.mjs` がつくる。実ブラウザで docs/sound/ を
そのまま動かすので、当日子どもが動かすコードと同じものを測ることになる。
"""

from voice_scale.measure import (
    NOTES,
    Measured,
    cents,
    detected_hz,
    interval_errors,
    measure,
    measure_scale,
    strongest_hz,
)

__all__ = [
    "NOTES",
    "Measured",
    "cents",
    "detected_hz",
    "interval_errors",
    "measure",
    "measure_scale",
    "strongest_hz",
]
