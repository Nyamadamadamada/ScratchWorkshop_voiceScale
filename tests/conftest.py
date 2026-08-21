"""テストで使う音をつくる。"""

import numpy as np
import pytest

from voice_scale.audio import SR


@pytest.fixture
def rng():
    return np.random.default_rng(0)


def 声(hz: float, sec: float = 1.0, gain: float = 0.6) -> np.ndarray:
    """倍音を持つ、人の声に近い合成音。"""
    t = np.arange(int(SR * sec)) / SR
    x = sum((1.0 / k) * np.sin(2.0 * np.pi * hz * k * t) for k in range(1, 6))
    return gain * x / np.max(np.abs(x))


def 滑る声(start: float = 200.0, octaves: float = 1.5, sec: float = 1.0) -> np.ndarray:
    """音程が上がり続ける声。音階にできない。"""
    hz = start * 2.0 ** np.linspace(0.0, octaves, int(SR * sec))
    return 0.5 * np.sin(2.0 * np.pi * np.cumsum(hz) / SR)


def ゆれる声(hz: float = 300.0, cents: float = 48.0, sec: float = 1.0) -> np.ndarray:
    """ビブラートのかかった声。多少ゆれても通す必要がある。"""
    t = np.arange(int(SR * sec)) / SR
    f = hz * 2.0 ** ((cents / 1200.0) * np.sin(2.0 * np.pi * 5.0 * t))
    return 0.5 * np.sin(2.0 * np.pi * np.cumsum(f) / SR)


def 拍手(rng: np.random.Generator) -> np.ndarray:
    """短い衝撃音。音程が存在しない。"""
    n = int(SR * 0.02)
    click = rng.standard_normal(n) * np.exp(-np.linspace(0, 8, n))
    return np.concatenate([0.9 * click, np.zeros(int(SR * 0.3))])


def ささやき声(rng: np.random.Generator) -> np.ndarray:
    """声帯が震えていないので、波が規則正しくならない。"""
    x = np.convolve(rng.standard_normal(SR), np.hanning(64), "same")
    return 0.3 * x / np.max(np.abs(x))


def いちばん強い周波数(x: np.ndarray, sr: int = SR) -> float:
    """倍音構成に左右されない、音の高さの指標。"""
    n = 1 << 18
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)), n=n))
    freq = np.fft.rfftfreq(n, 1.0 / sr)
    band = (freq > 50.0) & (freq < 20000.0)
    return float(freq[band][np.argmax(spectrum[band])])


def 半音差(a: float, b: float) -> float:
    return 12.0 * np.log2(a / b)
