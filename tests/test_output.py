"""ブラウザがつくった音を測って、狙いどおりか確かめる。

ここを読めば、このアプリが何を保証しているかが分かる。
測っているのは、当日子どもが動かすコードが実際に出した WAV そのもの。
"""

from __future__ import annotations

import pytest

from voice_scale.measure import cents, interval_errors, measure_scale

通る声 = ["子どもの声300Hz", "大人の低い声110Hz", "低い声130Hz", "高い声784Hz", "とても高い声990Hz"]


@pytest.fixture
def 音階(生成結果):
    def 取る(名前: str):
        assert 生成結果[名前]["report"]["ok"], f"{名前} が音階にならなかった"
        return 生成結果[名前]["report"], measure_scale(生成結果[名前]["dir"])

    return 取る


def test_声を入れると8つの音ができる(音階):
    _, measured = 音階("子どもの声300Hz")
    assert [m.file for m in measured] == ["do", "re", "mi", "fa", "so", "ra", "si", "do_high"]
    assert [m.name for m in measured] == ["ド", "レ", "ミ", "ファ", "ソ", "ラ", "シ", "高いド"]


@pytest.mark.parametrize("名前", 通る声)
def test_8つの音は同じ長さになる(音階, 名前):
    """Scratch の「音を鳴らす」は鳴り終わるまで次へ進まない。

    長さがばらつくとメロディのテンポが崩れる。リサンプリングは低い音ほど
    長くなるので、そろえる工程を省けない。
    """
    _, measured = 音階(名前)
    assert {m.sec for m in measured} == {0.5}


@pytest.mark.parametrize("名前", 通る声)
def test_ドレミの音程が正しく並ぶ(音階, 名前):
    _, measured = 音階(名前)
    狂い = {name: round(c, 1) for name, c in interval_errors(measured).items() if abs(c) > 15.0}
    assert not 狂い, f"音程がずれた: {狂い}"


@pytest.mark.parametrize("名前", 通る声)
def test_声の高さがそのまま活きる(音階, 名前):
    """録音した声と、できあがった「ド」の高さが上下6半音以内に収まること。

    ここが崩れると本人の声に聞こえなくなる。以前オクターブの範囲を C4〜C5 に
    絞っていたため、低い声は15半音持ち上げられ、高い声は逆にドが半オクターブ
    下がって「どーん」と鳴っていた。
    """
    report, _ = 音階(名前)
    ずれ = cents(report["base"], report["f0"]) / 100.0
    assert abs(ずれ) <= 6.0, f"{report['f0']:.0f}Hz が {ずれ:+.1f}半音 ずれる"


@pytest.mark.parametrize("名前", [*通る声, "短い声"])
def test_鳴り終わりがプチッと切れない(音階, 名前):
    """無音で埋める音にもフェードアウトが要る。

    掛けないと波形が振幅を持ったまま無音へ落ち、音が途中で切られたように
    聞こえる。短い録音では8音すべてが無音で埋まるので、全部に出る。
    """
    _, measured = 音階(名前)
    切れ = {m.file: round(m.tail, 3) for m in measured if m.tail > 0.01}
    assert not 切れ, f"鳴り終わりに段差がある: {切れ}"


@pytest.mark.parametrize("名前", 通る声)
def test_Scratchが読める形式で書き出す(音階, 名前):
    _, measured = 音階(名前)
    assert {(m.channels, m.sample_rate, m.bit_depth) for m in measured} == {(1, 44100, 16)}


@pytest.mark.parametrize("名前", 通る声)
def test_音量がそろう(音階, 名前):
    """声の大きい子と小さい子で、できあがる音の音量が変わらないようにする。"""
    _, measured = 音階(名前)
    for m in measured:
        assert m.peak == pytest.approx(0.708, abs=0.01)


@pytest.mark.parametrize(
    ("名前", "音名"),
    [
        ("子どもの声300Hz", "レ"),
        ("大人の低い声110Hz", "ラ"),
        ("低い声130Hz", "ド"),
        ("高い声784Hz", "ソ"),
    ],
)
def test_録音した声に近い音を言い当てる(音階, 名前, 音名):
    """画面に「君の声に近い音は◯」と出すために使う。"""
    report, _ = 音階(名前)
    assert report["nearest"]["name"] == 音名
    assert abs(report["nearest"]["cents"]) < 60.0
