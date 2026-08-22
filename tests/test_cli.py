"""測るコマンドのふるまい。"""

from __future__ import annotations

import shutil

import pytest

from voice_scale.cli import main


def test_正しい音階なら成功する(生成結果):
    assert main(["check", str(生成結果["子どもの声300Hz"]["dir"])]) == 0


def test_ファイルが足りなければ何が無いか教える(生成結果, tmp_path):
    for wav in list(生成結果["子どもの声300Hz"]["dir"].glob("*.wav"))[:5]:
        shutil.copy(wav, tmp_path)
    with pytest.raises(FileNotFoundError, match="に無い"):
        main(["check", str(tmp_path)])


def test_ないディレクトリを渡すと失敗する(tmp_path):
    assert main(["check", str(tmp_path / "ない")]) == 2
