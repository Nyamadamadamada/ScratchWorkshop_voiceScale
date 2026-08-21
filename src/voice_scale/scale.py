"""録音した1音から、ドレミファソラシドの8音をつくる。"""

from __future__ import annotations

import numpy as np

from voice_scale.audio import SR, fit_length, normalize, resample

C4 = 261.6256  # ド（C4）
NOTE_SEC = 0.5  # 四分音符の長さ。テンポ120にあたる
MAX_SOURCE_SEC = 1.0  # ここまでを素材として使う

# ファイル名がそのまま Scratch の音の名前になるので、子どもが読める日本語にする
NOTES: tuple[tuple[str, int], ...] = (
    ("ド", 0),
    ("レ", 2),
    ("ミ", 4),
    ("ファ", 5),
    ("ソ", 7),
    ("ラ", 9),
    ("シ", 11),
    ("高いド", 12),
)


# 基準にできるオクターブの範囲。C2(65Hz) から C5(523Hz) まで
MIN_OCTAVE = -2
MAX_OCTAVE = 1


def base_frequency(f0: float) -> tuple[float, int]:
    """基準になるドの周波数と、そのオクターブ番号のずれを返す。

    いちばん近いオクターブを選ぶ。声の高さをそのまま活かすため、
    変換の比は 0.52〜1.41倍に収まる。

    上限だけ C5 で止める。止めないと高い音源で基準が C6 まで上がり、
    最高音が2000Hzを超えて金切り声になる。

    下限を切ってはいけない。以前 0 で切っていたため、大人の低い声（110Hz）が
    15半音も持ち上げられ、まるで別人の声になっていた。
    """
    k = int(np.clip(round(np.log2(f0 / C4)), MIN_OCTAVE, MAX_OCTAVE))
    return C4 * 2.0**k, k


def build(
    x: np.ndarray,
    f0: float,
    sr: int = SR,
    note_sec: float = NOTE_SEC,
) -> dict[str, np.ndarray]:
    """8音ぶんの波形を名前つきで返す。すべて同じ長さになる。"""
    source = np.asarray(x, dtype=np.float64)[: int(sr * MAX_SOURCE_SEC)]
    base, _ = base_frequency(f0)
    length = round(sr * note_sec)

    out: dict[str, np.ndarray] = {}
    for name, semitone in NOTES:
        target = base * 2.0 ** (semitone / 12.0)
        out[name] = normalize(fit_length(resample(source, target / f0), length, sr))
    return out


def nearest_note(f0: float) -> tuple[str, float]:
    """録音した声にいちばん近い音の名前と、そのずれ[セント]を返す。

    声が基準の外にあっても、オクターブを折り返してから比べる。
    110Hz なら「ラ」になる。

    折り返す窓は4分音ぶん下げてある。基準のすぐ下にある声が
    「高いド」に回り込んでしまうのを防ぐため。ドと高いドは同じ音なので、
    低いほうの「ド」で答える。
    """
    base, _ = base_frequency(f0)
    low = base * 2.0 ** (-1.0 / 24.0)
    folded = f0
    while folded < low:
        folded *= 2.0
    while folded >= low * 2.0:
        folded /= 2.0

    def gap(note: tuple[str, int]) -> float:
        return abs(1200.0 * np.log2(folded / (base * 2.0 ** (note[1] / 12.0))))

    name, semitone = min((n for n in NOTES if n[1] < 12), key=gap)
    return name, 1200.0 * np.log2(folded / (base * 2.0 ** (semitone / 12.0)))
