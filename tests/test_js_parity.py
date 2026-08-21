"""JavaScript 版と Python 版が同じ結果を出すことを確かめる。

同じ入力を両方に通し、f0・有声率・ばらつき・判定を突き合わせる。
ここがずれていると、手元の見本と当日の子どもの結果が食い違う。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from conftest import tone

from voice_scale.audio import SR, fit_length, normalize, trim
from voice_scale.check import judge
from voice_scale.pitch import detect

ROOT = Path(__file__).resolve().parents[1]
JS_DIR = ROOT / "tests" / "js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node がない")


def build_cases() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(0)
    t = np.arange(SR) / SR
    vib = 300.0 * 2.0 ** (0.04 * np.sin(2.0 * np.pi * 5.0 * t))
    glide = 200.0 * 2.0 ** np.linspace(0.0, 1.5, SR)
    click = rng.standard_normal(int(SR * 0.02)) * np.exp(-np.linspace(0, 8, int(SR * 0.02)))
    return {
        "低い声130Hz": tone(130.81),
        "子どもの声300Hz": tone(300.0),
        "ラ440Hz": tone(440.0),
        "高い声784Hz": tone(783.99),
        "ビブラート": np.sin(2.0 * np.pi * np.cumsum(vib) / SR),
        "音程が滑る声": np.sin(2.0 * np.pi * np.cumsum(glide) / SR),
        "ホワイトノイズ": 0.5 * rng.standard_normal(SR),
        "小さすぎる声": 0.002 * tone(300.0),
        "短い衝撃音": np.concatenate([0.9 * click, np.zeros(int(SR * 0.3))]),
        "前後に無音がある声": np.concatenate(
            [np.zeros(SR // 2), tone(300.0, sec=0.6), np.zeros(SR // 2)]
        ),
    }


@pytest.fixture(scope="module")
def both():
    cases = build_cases()
    JS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        name: {"sr": SR, "samples": [round(float(v), 7) for v in x]} for name, x in cases.items()
    }
    (JS_DIR / "cases.json").write_text(json.dumps(payload), encoding="utf-8")

    proc = subprocess.run(
        ["node", str(JS_DIR / "cross_check.mjs")],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        pytest.fail(f"node が失敗した:\n{proc.stderr}")
    js = json.loads(proc.stdout)

    py = {}
    for name, x in cases.items():
        t = trim(x)
        p = detect(t, SR)
        py[name] = {
            "trimmed": len(t),
            "f0": p.f0,
            "voicedRatio": p.voiced_ratio,
            "spreadCents": p.spread_cents,
            "frames": p.frames,
            "reasons": judge(t, SR, p),
            "fitted": len(fit_length(t, 22050, 44100)),
            "peak": f"{float(np.max(normalize(t[:4096]))):.4f}",
        }
    return py, js


@pytest.mark.parametrize("name", list(build_cases()))
def test_無音カットの結果が一致(name, both):
    py, js = both
    assert py[name]["trimmed"] == js[name]["trimmed"]


@pytest.mark.parametrize("name", list(build_cases()))
def test_窓の数が一致(name, both):
    py, js = both
    assert py[name]["frames"] == js[name]["frames"]


@pytest.mark.parametrize("name", list(build_cases()))
def test_有声率が一致(name, both):
    py, js = both
    assert py[name]["voicedRatio"] == pytest.approx(js[name]["voicedRatio"], abs=0.02)


@pytest.mark.parametrize("name", list(build_cases()))
def test_f0が1セント以内で一致(name, both):
    py, js = both
    a, b = py[name]["f0"], js[name]["f0"]
    if not np.isfinite(a) or b is None or not np.isfinite(b):
        assert (not np.isfinite(a)) and (b is None or not np.isfinite(b))
        return
    assert abs(1200.0 * np.log2(a / b)) < 1.0


@pytest.mark.parametrize("name", list(build_cases()))
def test_判定が一致(name, both):
    py, js = both
    assert py[name]["reasons"] == js[name]["reasons"]


@pytest.mark.parametrize("name", list(build_cases()))
def test_長さそろえと音量そろえが一致(name, both):
    py, js = both
    assert py[name]["fitted"] == js[name]["fitted"]
    assert py[name]["peak"] == js[name]["peak"]
