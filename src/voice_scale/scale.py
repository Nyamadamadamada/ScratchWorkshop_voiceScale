"""録音した1音から、ドレミファソラシドの8音をつくる。

app/scale.js と対になる。
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

from voice_scale.audio import OUT_SR, fit_length, normalize, resample

C4 = 261.6256  # ド（C4）
NOTE_SEC = 0.5  # 四分音符の長さ。テンポ120にあたる
MAX_SOURCE_SEC = 1.0  # ここまでを素材として使う

# 基準にできるオクターブの範囲。C2(65Hz) から C6(1046Hz) まで。
# 音程検出が 80〜1000Hz を見るので、いちばん近いオクターブを選べば
# 必ずこの範囲に収まる。つまりこれは安全弁であって、声を曲げる制限ではない。
MIN_OCTAVE = -2
MAX_OCTAVE = 2


class Note(NamedTuple):
    """音階を構成する音の定義。"""

    name: str
    semitone: int


class Sound(NamedTuple):
    """できあがった1音。name がそのまま WAV のファイル名になる。"""

    name: str
    samples: np.ndarray


class Base(NamedTuple):
    """基準になるドの周波数と、C4 から見たオクターブのずれ。"""

    hz: float
    octave: int


class Nearest(NamedTuple):
    """録音した声にいちばん近い音と、そのずれ[セント]。"""

    name: str
    cents: float


# 名前がそのまま Scratch の音の名前になるので、子どもが読める日本語にする
NOTES: tuple[Note, ...] = (
    Note("ド", 0),
    Note("レ", 2),
    Note("ミ", 4),
    Note("ファ", 5),
    Note("ソ", 7),
    Note("ラ", 9),
    Note("シ", 11),
    Note("高いド", 12),
)


def base_frequency(f0: float) -> Base:
    """基準になるドを決める。いちばん近いオクターブを選ぶ。

    いちばん近いオクターブを選ぶので、変換の比は必ず 0.71〜1.41倍、
    つまり上下6半音以内に収まる。録音した声がそのまま楽器になる。

    範囲を狭めてはいけない。以前 C4〜C5 に絞っていたため、両端で声が壊れた。
    大人の低い声（110Hz）は15半音も持ち上げられ、高い声（990Hz）は逆に
    ドが半オクターブ下がって「どーん」と鳴り、本人の声に聞こえなくなった。

    代わりに、990Hz の高い声だと最高音が2093Hzまで上がる。ただしそれは
    その子自身の声を1オクターブ上げたものなので、作りものの金切り声とは違う。
    """
    octave = int(np.clip(round(np.log2(f0 / C4)), MIN_OCTAVE, MAX_OCTAVE))
    return Base(C4 * 2.0**octave, octave)


def build(
    x: np.ndarray,
    f0: float,
    sr: int = OUT_SR,
    note_sec: float = NOTE_SEC,
) -> list[Sound]:
    """8音ぶんの波形を NOTES の順で返す。すべて同じ長さになる。"""
    source = np.asarray(x, dtype=np.float64)[: int(sr * MAX_SOURCE_SEC)]
    base = base_frequency(f0)
    length = round(sr * note_sec)

    sounds = []
    for note in NOTES:
        target = base.hz * 2.0 ** (note.semitone / 12.0)
        shifted = resample(source, target / f0)
        sounds.append(Sound(note.name, normalize(fit_length(shifted, length, sr))))
    return sounds


def nearest_note(f0: float) -> Nearest:
    """録音した声にいちばん近い音を返す。

    声が基準の外にあっても、オクターブを折り返してから比べる。
    110Hz なら「ラ」になる。

    折り返す窓は4分音ぶん下げてある。基準のすぐ下にある声が「高いド」に
    回り込んでしまうのを防ぐため。ドと高いドは同じ音なので、低いほうで答える。
    """
    base = base_frequency(f0)
    low = base.hz * 2.0 ** (-1.0 / 24.0)
    folded = f0
    while folded < low:
        folded *= 2.0
    while folded >= low * 2.0:
        folded /= 2.0

    def cents_from(note: Note) -> float:
        return 1200.0 * np.log2(folded / (base.hz * 2.0 ** (note.semitone / 12.0)))

    within_octave = [n for n in NOTES if n.semitone < 12]
    closest = min(within_octave, key=lambda n: abs(cents_from(n)))
    return Nearest(closest.name, cents_from(closest))
