"""テストの下ごしらえ。

音をつくるのは docs/ の JavaScript なので、テストもまずブラウザを回して
WAV をつくらせる。そのあと Python でその WAV を測る。
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# ブラウザに通す入力。実際の子どもの声から、音階にできない音まで。
CASES = [
    {"id": "子どもの声300Hz", "tone": 300},
    {"id": "大人の低い声110Hz", "tone": 110},
    {"id": "低い声130Hz", "tone": 130.81},
    {"id": "高い声784Hz", "tone": 784},
    {"id": "とても高い声990Hz", "tone": 990},
    {"id": "短い声", "tone": 300, "sec": 0.25},
    {"id": "ホワイトノイズ", "noise": True},
    {"id": "小さすぎる声", "tone": 300, "gain": 0.003},
    {"id": "みじかすぎる声", "tone": 300, "sec": 0.1},
]

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node がない")


def 空きポート() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def 生成結果(tmp_path_factory) -> dict[str, dict]:
    """ブラウザを一度だけ立ち上げて、全ケースぶんの WAV をつくらせる。"""
    if shutil.which("node") is None:
        pytest.skip("node がない")

    port = 空きポート()
    server = subprocess.Popen(
        ["python", "-m", "http.server", "-d", str(ROOT / "docs"), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(50):  # 立ち上がるまで待つ
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.1)

        out = tmp_path_factory.mktemp("生成")
        specs = out / "specs.json"
        specs.write_text(json.dumps(CASES, ensure_ascii=False), encoding="utf-8")

        生成 = ROOT / "tools" / "generate.mjs"
        proc = subprocess.run(
            ["node", str(生成), "--batch", str(specs), "--out", str(out)],
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "BASE_URL": f"http://127.0.0.1:{port}/"},
            check=False,
        )
        if proc.returncode != 0:
            pytest.fail(f"generate.mjs が失敗した:\n{proc.stdout}\n{proc.stderr}")

        結果 = {}
        for case in CASES:
            d = out / case["id"]
            report = json.loads((d / "report.json").read_text(encoding="utf-8"))
            結果[case["id"]] = {"dir": d, "report": report}
        return 結果
    finally:
        server.terminate()
        server.wait(timeout=5)
