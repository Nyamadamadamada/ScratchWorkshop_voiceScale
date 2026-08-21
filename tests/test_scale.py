"""音階生成の検証。"""

import numpy as np
import pytest
from conftest import tone

from voice_scale.audio import SR
from voice_scale.scale import C4, NOTES, base_frequency, build


def strongest_hz(x: np.ndarray, sr: int = SR) -> float:
    """いちばん強い周波数成分。倍音構成に左右されない指標として使う。"""
    n = 1 << 18
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)), n=n))
    freq = np.fft.rfftfreq(n, 1.0 / sr)
    band = (freq > 50.0) & (freq < 20000.0)
    return float(freq[band][np.argmax(spectrum[band])])


@pytest.mark.parametrize("f0", [261.63, 300.0, 440.0, 523.25, 783.99])
def test_8音の長さがそろう(f0):
    notes = build(tone(f0), f0)
    lengths = {len(w) for w in notes.values()}
    assert len(lengths) == 1
    assert lengths.pop() == round(SR * 0.5)


@pytest.mark.parametrize("f0", [261.63, 300.0, 440.0, 783.99])
def test_音程差が正確(f0):
    """リサンプリングは全周波数を同じ比率で動かすので、音程差はずれない。"""
    notes = build(tone(f0), f0)
    base_hz = strongest_hz(notes["ド"])
    for name, semitone in NOTES:
        ratio = strongest_hz(notes[name]) / base_hz
        cents = 1200.0 * np.log2(ratio / 2.0 ** (semitone / 12.0))
        assert abs(cents) < 15.0, f"{name} が {cents:+.1f} セントずれた"


def test_基準はC4かC5に収まる():
    for f0 in (90.0, 130.0, 261.63, 400.0, 523.25, 784.0, 990.0):
        base, k = base_frequency(f0)
        assert k in (0, 1)
        assert base in (C4, C4 * 2.0)


def test_高い音源でも最高音が金切り声にならない():
    """基準を制限しないと C6 まで上がり、最高音が2000Hzを超える。"""
    base, _ = base_frequency(784.0)
    assert base * 2.0 <= C4 * 4.0 + 1e-6


def test_ドの高さが基準と一致する():
    f0 = 300.0
    notes = build(tone(f0), f0)
    base, _ = base_frequency(f0)
    assert abs(1200.0 * np.log2(strongest_hz(notes["ド"]) / base)) < 15.0


def test_音量がそろう():
    notes = build(tone(300.0), 300.0)
    for wave in notes.values():
        assert 0.6 < float(np.max(np.abs(wave))) < 0.8
