"""音階にできない音を弾けるかの検証。"""

import numpy as np
from conftest import tone

from voice_scale.audio import SR, trim
from voice_scale.check import judge
from voice_scale.pitch import detect


def verdict(x: np.ndarray) -> list[str]:
    return judge(x, SR, detect(x, SR))


def test_声は通る():
    assert verdict(tone(300.0)) == []


def test_ホワイトノイズは音程なしで弾く(rng):
    assert "unpitched" in verdict(0.5 * rng.standard_normal(SR))


def test_ささやき声は音程なしで弾く(rng):
    x = np.convolve(rng.standard_normal(SR), np.hanning(64), "same")
    assert "unpitched" in verdict(0.3 * x / np.max(np.abs(x)))


def test_短い衝撃音は弾く(rng):
    click = rng.standard_normal(int(SR * 0.02)) * np.exp(-np.linspace(0, 8, int(SR * 0.02)))
    x = np.concatenate([0.9 * click, np.zeros(int(SR * 0.3))])
    assert verdict(x) != []


def test_小さすぎる声は弾く():
    assert "quiet" in verdict(0.002 * tone(300.0))


def test_短すぎる声は弾く():
    assert "short" in verdict(tone(300.0, sec=0.1))


def test_音程が滑る声は弾く():
    hz = 200.0 * 2.0 ** np.linspace(0.0, 1.5, SR)
    assert "unstable" in verdict(np.sin(2.0 * np.pi * np.cumsum(hz) / SR))


def test_多少ゆれる声は通す():
    """教室で何度も弾かれると子どもが萎縮するので、緩めに通す。"""
    t = np.arange(SR) / SR
    hz = 300.0 * 2.0 ** (0.04 * np.sin(2.0 * np.pi * 5.0 * t))  # ±48セントのビブラート
    x = np.sin(2.0 * np.pi * np.cumsum(hz) / SR)
    assert verdict(x) == []


def test_無音は弾く():
    assert verdict(np.zeros(SR)) != []


def test_無音をトリムすると空になる():
    assert len(trim(np.zeros(SR))) == 0
