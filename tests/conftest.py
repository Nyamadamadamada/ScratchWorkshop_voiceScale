import numpy as np
import pytest

from voice_scale.audio import SR


@pytest.fixture
def rng():
    return np.random.default_rng(0)


def tone(hz: float, sec: float = 1.0, sr: int = SR, harmonics: int = 5) -> np.ndarray:
    """倍音を持つ、声に近い合成音をつくる。"""
    t = np.arange(int(sr * sec)) / sr
    x = np.zeros_like(t)
    for k in range(1, harmonics + 1):
        x += (1.0 / k) * np.sin(2.0 * np.pi * hz * k * t)
    return x / np.max(np.abs(x))
