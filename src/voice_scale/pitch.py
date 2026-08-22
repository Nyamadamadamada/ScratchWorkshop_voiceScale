"""YIN法による基本周波数の検出。

docs/pitch.js と対になる。同じ値を返すことは tests/test_parity.py で確認する。
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

WIN = 2048  # 窓長
HOP = 512  # ホップ
HALF = WIN // 2  # 相関を取る幅
THRESHOLD = 0.15  # d'(tau) がこれを下回れば有声とみなす
FMIN = 80.0
FMAX = 1000.0


class Pitch(NamedTuple):
    """検出結果。"""

    f0: float  # 有声窓の中央値[Hz]。有声窓がなければ nan
    voiced_ratio: float  # 有声と判定された窓の割合
    spread_cents: float  # 中央値からのばらつき[セント]
    frames: int  # 解析した窓の数


def frame_f0(frame: np.ndarray, sr: int) -> tuple[float, float]:
    """1窓ぶんの (f0[Hz], d'(tau)の値) を返す。

    d'(tau) が THRESHOLD を下回っていれば、その窓は有声とみなせる。
    """
    tau_min = max(1, int(np.ceil(sr / FMAX)))
    tau_max = min(HALF, int(np.floor(sr / FMIN)))
    if tau_max <= tau_min:
        return float("nan"), 1.0

    x = np.asarray(frame, dtype=np.float64)
    head = x[:HALF]

    # 差分関数 d(tau) = Σ (x[i] - x[i+tau])^2 を、相関と累積二乗和から組み立てる
    r = np.correlate(x, head, mode="valid")[: tau_max + 1]
    cumsq = np.concatenate(([0.0], np.cumsum(x * x)))
    taus = np.arange(tau_max + 1)
    power_head = cumsq[HALF] - cumsq[0]
    power_tail = cumsq[HALF + taus] - cumsq[taus]
    d = power_head + power_tail - 2.0 * r
    d[0] = 0.0

    # 累積平均正規化 d'(tau) = d(tau) * tau / Σ_{j=1..tau} d(j)
    cum = np.cumsum(d[1:])
    dp = np.ones_like(d)
    nz = cum > 0
    dp[1:][nz] = d[1:][nz] * taus[1:][nz] / cum[nz]

    # 閾値を最初に下回った谷を採る。なければ最小値
    tau = -1
    t = tau_min
    while t <= tau_max:
        if dp[t] < THRESHOLD:
            while t + 1 <= tau_max and dp[t + 1] < dp[t]:
                t += 1
            tau = t
            break
        t += 1
    if tau < 0:
        tau = int(tau_min + np.argmin(dp[tau_min : tau_max + 1]))

    confidence = float(dp[tau])

    # 放物線補間でサンプル間の位置を求める
    tau_f = float(tau)
    if tau_min < tau < tau_max:
        s0, s1, s2 = dp[tau - 1], dp[tau], dp[tau + 1]
        denom = 2.0 * (s0 - 2.0 * s1 + s2)
        if denom != 0.0:
            tau_f = tau + (s0 - s2) / denom

    if tau_f <= 0:
        return float("nan"), 1.0
    return sr / tau_f, confidence


def detect(x: np.ndarray, sr: int) -> Pitch:
    """波形全体から f0 と、判定に使う指標を求める。"""
    x = np.asarray(x, dtype=np.float64)
    if len(x) < WIN:
        return Pitch(float("nan"), 0.0, float("inf"), 0)

    values: list[float] = []
    frames = 0
    for start in range(0, len(x) - WIN + 1, HOP):
        f0, confidence = frame_f0(x[start : start + WIN], sr)
        frames += 1
        if confidence < THRESHOLD and FMIN <= f0 <= FMAX:
            values.append(f0)

    if not values:
        return Pitch(float("nan"), 0.0, float("inf"), frames)

    arr = np.asarray(values)
    median = float(np.median(arr))
    spread = float(np.median(np.abs(1200.0 * np.log2(arr / median))))
    return Pitch(median, len(values) / frames, spread, frames)
