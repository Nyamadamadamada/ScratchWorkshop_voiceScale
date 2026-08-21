"""音程検出の検証。"""

import numpy as np
import pytest
from conftest import tone

from voice_scale.audio import SR
from voice_scale.pitch import detect

# 子どもの声はおおむね250〜350Hz。その周辺を厚めに見る
FREQS = [90.0, 130.81, 220.0, 261.63, 300.0, 329.63, 440.0, 523.25, 783.99, 950.0]


@pytest.mark.parametrize("hz", FREQS)
def test_純音の検出誤差が1パーセント以内(hz):
    p = detect(tone(hz), SR)
    assert p.voiced_ratio > 0.9
    assert abs(p.f0 - hz) / hz < 0.01


@pytest.mark.parametrize("hz", FREQS)
def test_純音の検出誤差が10セント以内(hz):
    p = detect(tone(hz), SR)
    assert abs(1200.0 * np.log2(p.f0 / hz)) < 10.0


def test_ホワイトノイズは有声率が低い(rng):
    p = detect(rng.standard_normal(SR), SR)
    assert p.voiced_ratio < 0.5


def test_無音は検出できない():
    p = detect(np.zeros(SR), SR)
    assert not np.isfinite(p.f0)
    assert p.voiced_ratio == 0.0


def test_短すぎる波形は解析しない():
    p = detect(np.zeros(1000), SR)
    assert p.frames == 0


def test_音程が滑る声はばらつきが大きい():
    hz = 200.0 * 2.0 ** np.linspace(0.0, 1.5, SR)
    x = np.sin(2.0 * np.pi * np.cumsum(hz) / SR)
    assert detect(x, SR).spread_cents > 150.0


def test_安定した声はばらつきが小さい():
    assert detect(tone(300.0), SR).spread_cents < 10.0


def test_librosaと結果が一致する():
    """独立実装と突き合わせる。"""
    librosa = pytest.importorskip("librosa")
    for hz in (220.0, 330.0, 440.0):
        x = tone(hz)
        f0, voiced, _ = librosa.pyin(x, fmin=80, fmax=1000, sr=SR)
        expected = float(np.median(f0[voiced]))
        got = detect(x, SR).f0
        assert abs(1200.0 * np.log2(got / expected)) < 25.0
