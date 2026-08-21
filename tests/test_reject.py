"""音階にできない音を弾く、という異常系。

無声音やノイズは声帯が震えていないので波が規則正しくならず、
原理的に音程が存在しない。頑張っても音階にはできないので、
その場で言葉を返して録り直してもらう。
"""

import numpy as np
import pytest
from conftest import ささやき声, ゆれる声, 声, 拍手, 滑る声

from voice_scale.audio import SR, trim
from voice_scale.check import MESSAGES, judge
from voice_scale.pitch import detect


def 判定(x: np.ndarray) -> list[str]:
    x = trim(x)
    return judge(x, SR, detect(x, SR))


def test_ふつうの声は通る():
    assert 判定(声(300.0)) == []


def test_多少ゆれる声も通す():
    """教室で何度も弾かれると子どもが萎縮する。

    原理的に無理なものだけ確実に止め、ビブラート程度は通す。
    ばらつきの閾値を150セントと緩めに取っているのはこのため。
    """
    assert 判定(ゆれる声(cents=48.0)) == []


def test_ノイズは音程がないので弾く(rng):
    assert 判定(0.5 * rng.standard_normal(SR)) == ["unpitched"]


def test_ささやき声は弾く(rng):
    assert 判定(ささやき声(rng)) == ["unpitched"]


def test_拍手のような短い音は弾く(rng):
    assert "unpitched" in 判定(拍手(rng))


def test_遠くて小さい声は弾く():
    assert "quiet" in 判定(声(300.0, gain=0.003))


def test_短すぎる声は弾く():
    assert "short" in 判定(声(300.0, sec=0.1))


def test_音程が滑る声は弾く():
    assert 判定(滑る声()) == ["unstable"]


def test_無音は弾く():
    assert 判定(np.zeros(SR)) != []


@pytest.mark.parametrize("key", ["quiet", "short", "unpitched", "unstable"])
def test_弾いた理由には子ども向けの文言がある(key):
    assert MESSAGES[key].endswith("てね")
