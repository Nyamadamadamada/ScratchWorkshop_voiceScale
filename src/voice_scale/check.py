"""音階にできない音を弾く。

docs/check.js と対になる。

無声音やノイズは声帯が震えていないので波が規則正しくならず、
原理的に音程が存在しない。
"""

from __future__ import annotations

import numpy as np

from voice_scale.pitch import Pitch

MIN_PEAK = 0.01  # これ未満は小さすぎる
MIN_SEC = 0.15  # これ未満は短すぎる
MIN_VOICED = 0.50  # 有声窓がこの割合を下回れば音程なし
MAX_SPREAD_CENTS = 150.0  # 中央値からのばらつきの上限

# 教室で何度も弾かれると子どもが萎縮する。原理的に無理なものだけ確実に止め、
# 多少音程が動く程度は通す。閾値150セントはそのために緩めに取ってある。

MESSAGES = {
    "quiet": "もっと近くで声を出してね",
    "short": "もう少し長く声を出してね",
    "unpitched": "「あー」や「にゃー」のように声をのばしてね",
    "unstable": "同じ高さで声を出してね",
}


def judge(x: np.ndarray, sr: int, pitch: Pitch) -> list[str]:
    """弾く理由のキーを並べて返す。空なら音階にできる。"""
    reasons: list[str] = []
    x = np.asarray(x, dtype=np.float64)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0

    if peak < MIN_PEAK:
        reasons.append("quiet")
    if len(x) / sr < MIN_SEC:
        reasons.append("short")
    if pitch.voiced_ratio < MIN_VOICED or not np.isfinite(pitch.f0):
        reasons.append("unpitched")
    elif pitch.spread_cents > MAX_SPREAD_CENTS:
        reasons.append("unstable")
    return reasons
