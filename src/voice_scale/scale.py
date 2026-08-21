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


def base_frequency(f0: float) -> tuple[float, int]:
    """基準になるドの周波数と、そのオクターブ番号のずれを返す。

    C4 か C5 に必ず収める。制限しないと、高い音源では基準が C6 まで上がり
    最高音が2000Hzを超えて金切り声になる。
    """
    k = int(np.clip(round(np.log2(f0 / C4)), 0, 1))
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
