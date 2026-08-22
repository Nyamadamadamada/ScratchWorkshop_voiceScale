"""波形の長さ・音量をそろえる処理。

docs/audio.js と対になる。どちらも同じ結果を返す。
"""

from __future__ import annotations

import numpy as np

OUT_SR = 44100  # 書き出す WAV のレート。Python 版は読み込みもここへそろえる
FADE_IN_MS = 10.0
FADE_OUT_MS = 30.0
PEAK_DB = -3.0
TRIM_TOP_DB = 35.0


def resample(x: np.ndarray, ratio: float) -> np.ndarray:
    """再生速度を ratio 倍にする。線形補間。

    ratio が大きいほど音は高く、そして短くなる。これが音階をつくる中心の処理で、
    サンプラーという楽器が昔からやっている方式と同じ。

    ブラウザ側は同じことを OfflineAudioContext の playbackRate で行う。
    """
    x = np.asarray(x, dtype=np.float64)
    if len(x) < 2 or ratio <= 0:
        return x.copy()
    return np.interp(np.arange(0.0, len(x) - 1, ratio), np.arange(len(x)), x)


def trim(x: np.ndarray, top_db: float = TRIM_TOP_DB, frame: int = 1024, hop: int = 256):
    """前後の無音を削る。

    閾値はピーク音量からの相対値にする。
    """
    x = np.asarray(x, dtype=np.float64)
    if len(x) < frame:
        return x
    count = 1 + (len(x) - frame) // hop
    index = np.arange(frame)[None, :] + hop * np.arange(count)[:, None]
    rms = np.sqrt((x[index] ** 2).mean(axis=1))
    if rms.max() <= 0.0:
        return x[:0]
    keep = np.nonzero(rms >= rms.max() * 10.0 ** (-top_db / 20.0))[0]
    if len(keep) == 0:
        return x[:0]
    start = int(keep[0]) * hop
    end = min(len(x), int(keep[-1]) * hop + frame)
    return x[start:end].copy()


def fit_length(x: np.ndarray, n: int, sr: int = OUT_SR) -> np.ndarray:
    """長さを n サンプルちょうどにそろえる。

    Scratch の「音を鳴らす」は鳴り終わるまで次へ進まないため、
    8音の長さがそろっていないとメロディのテンポが崩れる。
    リサンプリングは低い音ほど長くなるので、この工程を省けない。
    """
    x = np.asarray(x, dtype=np.float64)
    if n <= 0:
        return x[:0]
    out = np.zeros(n)
    end = min(len(x), n)
    out[:end] = x[:end]

    # 鳴り終わりには必ずフェードをかける。無音で埋めるときも要る。
    # 掛けないと波形が振幅を持ったまま無音へ落ち、「プチッ」と鳴って
    # 音が途中で切られたように聞こえる。
    fade_out = min(int(sr * FADE_OUT_MS / 1000.0), end)
    if fade_out > 1:
        out[end - fade_out : end] *= np.linspace(1.0, 0.0, fade_out)
    fade_in = min(int(sr * FADE_IN_MS / 1000.0), end)
    if fade_in > 1:
        out[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    return out


def normalize(x: np.ndarray, peak_db: float = PEAK_DB) -> np.ndarray:
    """ピークを peak_db にそろえる。声の大小で音量が変わらないようにする。"""
    x = np.asarray(x, dtype=np.float64)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak <= 0.0:
        return x
    return x * (10.0 ** (peak_db / 20.0) / peak)
