"""できあがった WAV を測る。

音をつくるのは docs/ の JavaScript だけ。Python はそれが出した WAV を読んで、
狙いどおりになっているか測る側に回る。同じ処理を二度書かないための分担。

音の高さは librosa で測る。docs/sound/pitch.js とは別のものさしを当てることで、
検出そのものが間違っていないかも同時に確かめられる。
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import NamedTuple

import numpy as np
import soundfile as sf

warnings.filterwarnings("ignore", module="librosa")

# 長調の音階。docs/sound/scale.js の NOTES と同じ並び。
NOTES: tuple[tuple[str, str, int], ...] = (
    ("ド", "do", 0),
    ("レ", "re", 2),
    ("ミ", "mi", 4),
    ("ファ", "fa", 5),
    ("ソ", "so", 7),
    ("ラ", "ra", 9),
    ("シ", "si", 11),
    ("高いド", "do_high", 12),
)


class Measured(NamedTuple):
    """WAV 1つぶんの測定結果。"""

    name: str
    file: str
    sec: float  # ファイルの長さ
    sounding_sec: float  # 実際に音が出ている長さ
    peak: float
    hz: float  # いちばん強い周波数成分
    tail: float  # 鳴り終わりの振幅。大きいとプチッと鳴る
    channels: int
    sample_rate: int
    bit_depth: int


def cents(hz: float, reference: float) -> float:
    """2つの周波数の隔たりをセントで返す。100セントが半音。"""
    return 1200.0 * np.log2(hz / reference)


def strongest_hz(x: np.ndarray, sr: int) -> float:
    """いちばん強い周波数成分。倍音の構成に左右されない指標として使う。"""
    n = 1 << 18
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)), n=n))
    freq = np.fft.rfftfreq(n, 1.0 / sr)
    band = (freq > 50.0) & (freq < 20000.0)
    return float(freq[band][np.argmax(spectrum[band])])


def detected_hz(x: np.ndarray, sr: int) -> float:
    """librosa による基本周波数。別のものさしとして使う。"""
    import librosa

    f0, voiced, _ = librosa.pyin(x, fmin=60, fmax=4000, sr=sr)
    return float(np.median(f0[voiced])) if voiced.any() else float("nan")


def measure(path: str | Path) -> Measured:
    """WAV を1つ測る。"""
    path = Path(path)
    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    info = sf.info(str(path))
    mono = x.mean(axis=1)

    loud = np.nonzero(np.abs(mono) > 1e-4)[0]
    end = int(loud[-1]) if len(loud) else 0
    name = next((n for n, f, _ in NOTES if f == path.stem), path.stem)

    return Measured(
        name=name,
        file=path.stem,
        sec=len(mono) / sr,
        sounding_sec=(end + 1) / sr,
        peak=float(np.max(np.abs(mono))) if len(mono) else 0.0,
        hz=strongest_hz(mono, sr),
        tail=float(abs(mono[end])) if len(mono) else 0.0,
        channels=info.channels,
        sample_rate=sr,
        bit_depth=16 if info.subtype == "PCM_16" else 0,
    )


def measure_scale(directory: str | Path) -> list[Measured]:
    """8音ぶんを NOTES の順で測る。足りないファイルがあれば知らせる。"""
    directory = Path(directory)
    missing = [f for _, f, _ in NOTES if not (directory / f"{f}.wav").exists()]
    if missing:
        raise FileNotFoundError(f"{directory} に無い: {' '.join(missing)}")
    return [measure(directory / f"{f}.wav") for _, f, _ in NOTES]


def interval_errors(measured: list[Measured]) -> dict[str, float]:
    """ドから見た音程の狂いをセントで返す。0に近いほど正しい音階。"""
    base = measured[0].hz
    return {
        m.name: cents(m.hz / base, 2.0 ** (semitone / 12.0))
        for m, (_, _, semitone) in zip(measured, NOTES, strict=True)
    }
