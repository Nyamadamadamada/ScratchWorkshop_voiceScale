"""コマンドのふるまい。見本音源をつくるときに使う。"""

import numpy as np
from conftest import 声

from voice_scale import wav
from voice_scale.audio import OUT_SR
from voice_scale.cli import main


def 音源(tmp_path, x, name="test.wav"):
    path = tmp_path / name
    wav.write(path, x, OUT_SR)
    return path


def test_声を渡すと8つのWAVができる(tmp_path):
    src = 音源(tmp_path, 声(300.0))
    out = tmp_path / "見本"
    assert main(["build", str(src), "-o", str(out)]) == 0
    できた = sorted(p.name for p in out.glob("*.wav"))
    assert できた == sorted(
        ["ド.wav", "レ.wav", "ミ.wav", "ファ.wav", "ソ.wav", "ラ.wav", "シ.wav", "高いド.wav"]
    )


def test_音階にできない音は書き出さずに失敗する(tmp_path, rng):
    src = 音源(tmp_path, 0.5 * rng.standard_normal(OUT_SR))
    out = tmp_path / "見本"
    assert main(["build", str(src), "-o", str(out)]) == 1
    assert not out.exists()


def test_ファイルがなければ失敗する(tmp_path):
    assert main(["info", str(tmp_path / "ない.wav")]) == 2


def test_infoは音階にできるかを終了コードで返す(tmp_path, rng):
    assert main(["info", str(音源(tmp_path, 声(300.0), "ok.wav"))]) == 0
    assert main(["info", str(音源(tmp_path, np.zeros(OUT_SR), "ng.wav"))]) == 1


def test_1音の長さを変えられる(tmp_path):
    """当日の教材のテンポに合わせて調整するための逃げ道。"""
    import soundfile as sf

    src = 音源(tmp_path, 声(300.0))
    out = tmp_path / "見本"
    assert main(["build", str(src), "-o", str(out), "--note-sec", "1.0"]) == 0
    x, sr = sf.read(out / "ド.wav")
    assert len(x) == sr
