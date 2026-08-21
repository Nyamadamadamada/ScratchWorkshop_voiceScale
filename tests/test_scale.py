"""声から音階をつくる、というアプリの本筋のふるまい。

ここを読めば、このアプリが何を保証しているかが分かるようにしてある。
"""

import numpy as np
import pytest
from conftest import いちばん強い周波数, 半音差, 声

from voice_scale.audio import SR
from voice_scale.pitch import detect
from voice_scale.scale import NOTE_SEC, NOTES, base_frequency, build, nearest_note

# 大人の低い声から子どもの高い声まで
声の高さ = [85.0, 110.0, 130.81, 200.0, 300.0, 440.0, 784.0, 1000.0]


def 音階をつくる(hz: float):
    x = 声(hz)
    return build(x, detect(x, SR).f0)


def test_声を入れると8つの音ができる():
    notes = 音階をつくる(300.0)
    assert list(notes) == ["ド", "レ", "ミ", "ファ", "ソ", "ラ", "シ", "高いド"]


@pytest.mark.parametrize("hz", 声の高さ)
def test_8つの音は同じ長さになる(hz):
    """Scratch の「音を鳴らす」は鳴り終わるまで次へ進まない。

    長さがばらつくとメロディのテンポが崩れるので、そろえる工程が要る。
    リサンプリングは低い音ほど長くなるため、放っておくとそろわない。
    """
    lengths = {len(w) for w in 音階をつくる(hz).values()}
    assert lengths == {round(SR * NOTE_SEC)}


@pytest.mark.parametrize("hz", 声の高さ)
def test_ドレミの音程が正しく並ぶ(hz):
    notes = 音階をつくる(hz)
    ド = いちばん強い周波数(notes["ド"])
    ずれ = {
        name: 1200.0 * np.log2(いちばん強い周波数(notes[name]) / ド / 2.0 ** (semitone / 12.0))
        for name, semitone in NOTES
    }
    悪い = {k: round(v, 1) for k, v in ずれ.items() if abs(v) > 15.0}
    assert not 悪い, f"音程がずれた: {悪い}"


@pytest.mark.parametrize("hz", 声の高さ)
def test_声の高さがそのまま活きる(hz):
    """録音した声と、できあがった「ド」の高さが大きく離れないこと。

    以前は基準を C4 に固定していたため、大人の低い声（110Hz）が15半音も
    持ち上げられ、まるで別人の声になっていた。上へ大きくずらさないことが要件。
    """
    base, _ = base_frequency(hz)
    assert 半音差(base, hz) <= 6.0, f"{hz}Hz が {半音差(base, hz):.1f}半音 高くなる"


@pytest.mark.parametrize("hz", 声の高さ)
def test_高い声でも耳に刺さる音にならない(hz):
    """基準の上限を外すと、高い声で最高音が2000Hzを超えて金切り声になる。"""
    base, _ = base_frequency(hz)
    assert base * 2.0 <= 1100.0


@pytest.mark.parametrize(
    ("hz", "音名"),
    [
        (261.63, "ド"),
        (329.63, "ミ"),
        (392.00, "ソ"),
        (440.00, "ラ"),
        (110.00, "ラ"),  # 基準より低くても、折り返して言い当てる
        (130.81, "ド"),  # 基準のすぐ下。「高いド」に回り込ませない
        (880.00, "ラ"),
    ],
)
def test_録音した声に近い音を言い当てる(hz, 音名):
    """画面に「君の声に近い音は◯◯」と出すために使う。"""
    name, cents = nearest_note(hz)
    assert (name, abs(cents) < 10.0) == (音名, True)


def test_音量がそろう():
    """声の大きい子と小さい子で、できあがる音の音量が変わらないようにする。"""
    小さい声 = 音階をつくる(300.0)
    for wave in 小さい声.values():
        assert float(np.max(np.abs(wave))) == pytest.approx(0.708, abs=0.01)
