"""WAV の読み書き。

docs/wav.js と対になる。ブラウザ側は書き出しだけなので、
読み込みはこちらにしかない。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from voice_scale.audio import OUT_SR, resample


def load(path: str | Path, sr: int = OUT_SR) -> np.ndarray:
    """音声ファイルをモノラルの float 波形として読む。"""
    data, file_sr = sf.read(str(path), dtype="float64", always_2d=True)
    x = data.mean(axis=1)
    if file_sr != sr:
        x = resample(x, file_sr / sr)
    return x


def write(path: str | Path, x: np.ndarray, sr: int = OUT_SR) -> None:
    """16bit PCM・モノラルの WAV として書き出す。Scratch がそのまま読める。"""
    sf.write(str(path), np.asarray(x, dtype=np.float64), sr, subtype="PCM_16")
