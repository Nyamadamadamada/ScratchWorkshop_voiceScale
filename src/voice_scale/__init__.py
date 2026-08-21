"""声から音階をつくる。

docs/ に置いた JavaScript 版と同じ処理を Python で実装したもの。
アルゴリズムの検証と、見本音源の生成に使う。
"""

from voice_scale.check import MESSAGES, judge
from voice_scale.pitch import Pitch, detect
from voice_scale.scale import NOTE_SEC, NOTES, base_frequency, build

__all__ = [
    "MESSAGES",
    "NOTES",
    "NOTE_SEC",
    "Pitch",
    "base_frequency",
    "build",
    "detect",
    "judge",
]
