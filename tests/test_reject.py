"""音階にできない音を弾く、という異常系。

無声音やノイズは声帯が震えていないので波が規則正しくならず、
原理的に音程が存在しない。頑張っても音階にはできないので、
その場で言葉を返して録り直してもらう。

判定しているのはブラウザ側（docs/sound/check.js）。ここではその答えを見る。
"""

from __future__ import annotations

import pytest

弾く音 = {
    "ホワイトノイズ": "のばしてね",
    "小さすぎる声": "近くで",
    "みじかすぎる声": "長く",
}


@pytest.mark.parametrize("名前", ["子どもの声300Hz", "大人の低い声110Hz", "短い声"])
def test_声は通る(生成結果, 名前):
    assert 生成結果[名前]["report"]["ok"], 生成結果[名前]["report"].get("messages")


@pytest.mark.parametrize(("名前", "文言"), list(弾く音.items()))
def test_音階にできない音は弾く(生成結果, 名前, 文言):
    report = 生成結果[名前]["report"]
    assert not report["ok"], f"{名前} が通ってしまった"
    assert any(文言 in m for m in report["messages"]), report["messages"]


@pytest.mark.parametrize("名前", list(弾く音))
def test_弾いたときはWAVを書き出さない(生成結果, 名前):
    残り = list(生成結果[名前]["dir"].glob("*.wav"))
    assert not 残り, f"弾いたのに書き出している: {残り}"


@pytest.mark.parametrize("名前", list(弾く音))
def test_弾いた理由は子ども向けの文言で返す(生成結果, 名前):
    for message in 生成結果[名前]["report"]["messages"]:
        assert message.endswith("てね"), message
