"""声から音階をつくる、というアプリの本筋のふるまい。

ここを読めば、このアプリが何を保証しているかが分かるようにしてある。
"""

import numpy as np
import pytest
from conftest import いちばん強い周波数, 半音差, 声

from voice_scale.audio import OUT_SR
from voice_scale.pitch import detect
from voice_scale.scale import NOTE_SEC, NOTES, base_frequency, build, nearest_note

# 大人の低い声から子どもの高い声まで
声の高さ = [85.0, 110.0, 130.81, 200.0, 300.0, 440.0, 784.0, 1000.0]


def 音階をつくる(hz: float) -> dict[str, np.ndarray]:
    x = 声(hz)
    return {sound.name: sound.samples for sound in build(x, detect(x, OUT_SR).f0)}


def test_声を入れると8つの音ができる():
    x = 声(300.0)
    sounds = build(x, detect(x, OUT_SR).f0)
    assert [s.name for s in sounds] == ["ド", "レ", "ミ", "ファ", "ソ", "ラ", "シ", "高いド"]


@pytest.mark.parametrize("hz", 声の高さ)
def test_8つの音は同じ長さになる(hz):
    """Scratch の「音を鳴らす」は鳴り終わるまで次へ進まない。

    長さがばらつくとメロディのテンポが崩れるので、そろえる工程が要る。
    リサンプリングは低い音ほど長くなるため、放っておくとそろわない。
    """
    lengths = {len(w) for w in 音階をつくる(hz).values()}
    assert lengths == {round(OUT_SR * NOTE_SEC)}


@pytest.mark.parametrize("hz", 声の高さ)
def test_ドレミの音程が正しく並ぶ(hz):
    notes = 音階をつくる(hz)
    ド = いちばん強い周波数(notes["ド"])
    ずれ = {
        note.name: 1200.0
        * np.log2(いちばん強い周波数(notes[note.name]) / ド / 2.0 ** (note.semitone / 12.0))
        for note in NOTES
    }
    悪い = {k: round(v, 1) for k, v in ずれ.items() if abs(v) > 15.0}
    assert not 悪い, f"音程がずれた: {悪い}"


@pytest.mark.parametrize("hz", 声の高さ)
def test_声の高さがそのまま活きる(hz):
    """録音した声と、できあがった「ド」の高さが上下6半音以内に収まること。

    ここが崩れると、本人の声に聞こえなくなる。以前オクターブの範囲を C4〜C5 に
    絞っていたため、低い声（110Hz）は15半音持ち上げられ、高い声（990Hz）は
    ドが半オクターブ下がって「どーん」と鳴っていた。
    """
    ずれ = 半音差(base_frequency(hz).hz, hz)
    assert abs(ずれ) <= 6.0, f"{hz}Hz が {ずれ:+.1f}半音 ずれる"


@pytest.mark.parametrize("hz", 声の高さ)
def test_鳴り終わりがプチッと切れない(hz):
    """無音で埋める音にもフェードアウトが要る。

    掛けないと波形が振幅を持ったまま無音へ落ち、音が途中で切られたように
    聞こえる。短い録音では8音すべてが無音で埋まるので、全部に出る。
    """
    for sound in build(声(hz, sec=0.25), hz):
        鳴っている = np.nonzero(np.abs(sound.samples) > 1e-4)[0]
        assert abs(sound.samples[鳴っている[-1]]) < 0.01


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
    near = nearest_note(hz)
    assert (near.name, abs(near.cents) < 10.0) == (音名, True)


def test_音量がそろう():
    """声の大きい子と小さい子で、できあがる音の音量が変わらないようにする。"""
    小さい声 = 音階をつくる(300.0)
    for wave in 小さい声.values():
        assert float(np.max(np.abs(wave))) == pytest.approx(0.708, abs=0.01)
