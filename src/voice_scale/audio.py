"""波形の入出力と、長さ・音量をそろえる処理。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
FADE_IN_MS = 10.0
FADE_OUT_MS = 30.0
PEAK_DB = -3.0
TRIM_TOP_DB = 35.0


def resample(x: np.ndarray, ratio: float) -> np.ndarray:
    """再生速度を ratio 倍にする。線形補間。

    ratio が大きいほど音は高く、そして短くなる。
    """
    x = np.asarray(x, dtype=np.float64)
    if len(x) < 2 or ratio <= 0:
        return x.copy()
    idx = np.arange(0.0, len(x) - 1, ratio)
    return np.interp(idx, np.arange(len(x)), x)


def load(path: str | Path, sr: int = SR) -> np.ndarray:
    """音声ファイルをモノラルの float 波形として読む。"""
    data, file_sr = sf.read(str(path), dtype="float64", always_2d=True)
    x = data.mean(axis=1)
    if file_sr != sr:
        x = resample(x, file_sr / sr)
    return x


def write_wav(path: str | Path, x: np.ndarray, sr: int = SR) -> None:
    """16bit PCM・モノラルの WAV として書き出す。"""
    sf.write(str(path), np.asarray(x, dtype=np.float64), sr, subtype="PCM_16")


def trim(x: np.ndarray, top_db: float = TRIM_TOP_DB, frame: int = 1024, hop: int = 256):
    """前後の無音を削る。

    閾値はピーク音量からの相対値にする。会場は子どもが十数人いて暗騒音が
    大きいため、絶対値の閾値ではカットが効かなくなる。
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


def fit_length(x: np.ndarray, n: int, sr: int = SR) -> np.ndarray:
    """長さを n サンプルちょうどにそろえる。

    Scratch の「音を鳴らす」は鳴り終わるまで次へ進まないため、
    8音の長さがそろっていないとメロディのテンポが崩れる。
    """
    x = np.asarray(x, dtype=np.float64)
    if n <= 0:
        return x[:0]
    if len(x) > n:
        x = x[:n].copy()
        fade = min(int(sr * FADE_OUT_MS / 1000.0), n)
        if fade > 1:
            x[-fade:] *= np.linspace(1.0, 0.0, fade)
    else:
        x = np.pad(x, (0, n - len(x)))
    fade = min(int(sr * FADE_IN_MS / 1000.0), n)
    if fade > 1:
        x[:fade] *= np.linspace(0.0, 1.0, fade)
    return x


def normalize(x: np.ndarray, peak_db: float = PEAK_DB) -> np.ndarray:
    """ピークを peak_db にそろえる。"""
    x = np.asarray(x, dtype=np.float64)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if peak <= 0.0:
        return x
    return x * (10.0 ** (peak_db / 20.0) / peak)
