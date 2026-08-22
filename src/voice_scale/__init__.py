"""声から音階をつくる。

docs/ に置いた JavaScript 版と1対1で対応する。同じ名前のファイルに
同じ処理が入っていて、同じ値を返す。ずれていないことは
tests/test_parity.py で確かめる。

    pitch  声の高さを測る        docs/pitch.js
    check  音階にできるか判定する  docs/check.js
    audio  長さと音量をそろえる    docs/audio.js
    scale  8音をつくる           docs/scale.js
    wav    WAV を読み書きする     docs/wav.js
    cli    入り口                docs/app.js

Python 版は見本音源づくりと検証に使う。当日子どもが触るのは JavaScript 版。
"""

from voice_scale.check import MESSAGES, judge
from voice_scale.pitch import Pitch, detect
from voice_scale.scale import NOTE_SEC, NOTES, Nearest, Sound, base_frequency, build, nearest_note

__all__ = [
    "MESSAGES",
    "NOTES",
    "NOTE_SEC",
    "Nearest",
    "Pitch",
    "Sound",
    "base_frequency",
    "build",
    "detect",
    "judge",
    "nearest_note",
]
