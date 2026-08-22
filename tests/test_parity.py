"""ブラウザで動く JavaScript と、手元で動く Python が同じ結果を出すこと。

ここがずれると、講師が手元でつくった見本と、当日子どもの画面で
できあがるものが食い違う。同じ入力を両方に通して突き合わせる。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from conftest import ささやき声, ゆれる声, 声, 拍手, 滑る声

from voice_scale.audio import OUT_SR, fit_length, normalize, trim
from voice_scale.check import judge
from voice_scale.pitch import detect
from voice_scale.scale import base_frequency, nearest_note

JS_DIR = Path(__file__).resolve().parent / "js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node がない")


def 入力一式() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(0)
    return {
        "大人の低い声110Hz": 声(110.0),
        "子どもの声300Hz": 声(300.0),
        "高い声784Hz": 声(783.99),
        "ビブラート": ゆれる声(),
        "音程が滑る声": 滑る声(),
        "ホワイトノイズ": 0.5 * rng.standard_normal(OUT_SR),
        "ささやき声": ささやき声(rng),
        "拍手": 拍手(rng),
        "小さすぎる声": 声(300.0, gain=0.002),
        "前後に無音がある声": np.concatenate(
            [np.zeros(OUT_SR // 2), 声(300.0, sec=0.6), np.zeros(OUT_SR // 2)]
        ),
    }


def fitted(x: np.ndarray) -> dict:
    """長さと音量をそろえたあと、鳴り終わりの振幅がどうなるか。

    フェードが抜けているとここに差が出る。
    """
    out = normalize(fit_length(x, 22050, 44100))
    loud = np.nonzero(np.abs(out) > 1e-4)[0]
    end = float(abs(out[loud[-1]])) if len(loud) else 0.0
    return {"length": len(out), "end": round(end, 4)}


@pytest.fixture(scope="module")
def 両方の結果():
    cases = 入力一式()
    JS_DIR.mkdir(parents=True, exist_ok=True)
    (JS_DIR / "cases.json").write_text(
        json.dumps(
            {
                n: {"sr": OUT_SR, "samples": [round(float(v), 7) for v in x]}
                for n, x in cases.items()
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["node", str(JS_DIR / "cross_check.mjs")], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        pytest.fail(f"node が失敗した:\n{proc.stderr}")
    js = json.loads(proc.stdout)

    py = {}
    for name, x in cases.items():
        t = trim(x)
        p = detect(t, OUT_SR)
        ok = np.isfinite(p.f0)
        py[name] = {
            "trimmed": len(t),
            "frames": p.frames,
            "voicedRatio": p.voiced_ratio,
            "f0": p.f0 if ok else None,
            "reasons": judge(t, OUT_SR, p),
            "base": base_frequency(p.f0).hz if ok else None,
            "near": nearest_note(p.f0).name if ok else None,
            "fitted": fitted(t),
        }
    return py, js


def 突き合わせ(両方, key, 一致する):
    py, js = 両方
    違い = {n: (py[n][key], js[n][key]) for n in py if not 一致する(py[n][key], js[n][key])}
    assert not 違い, f"{key} が食い違った: {違い}"


def test_無音の削りかたが一致する(両方の結果):
    突き合わせ(両方の結果, "trimmed", lambda a, b: a == b)
    突き合わせ(両方の結果, "frames", lambda a, b: a == b)


def test_声の高さの検出が一致する(両方の結果):
    突き合わせ(
        両方の結果,
        "f0",
        lambda a, b: (
            (a is None and b is None)
            or (a is not None and b is not None and abs(1200.0 * np.log2(a / b)) < 1.0)
        ),
    )
    突き合わせ(両方の結果, "voicedRatio", lambda a, b: abs(a - b) < 0.02)


def test_音階にできるかの判定が一致する(両方の結果):
    突き合わせ(両方の結果, "reasons", lambda a, b: a == b)


def test_長さと音量のそろえかたが一致する(両方の結果):
    突き合わせ(
        両方の結果,
        "fitted",
        lambda a, b: a["length"] == b["length"] and abs(a["end"] - b["end"]) < 0.002,
    )


def test_基準の音と近い音の答えが一致する(両方の結果):
    突き合わせ(両方の結果, "base", lambda a, b: a == b or abs((a or 0) - (b or 0)) < 0.01)
    突き合わせ(両方の結果, "near", lambda a, b: a == b)
