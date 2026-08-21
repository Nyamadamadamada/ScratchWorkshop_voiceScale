"""コマンドライン。

voice-scale info  素材/にゃー.mp3
voice-scale build 素材/にゃー.mp3 -o 見本/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from voice_scale.audio import SR, load, trim, write_wav
from voice_scale.check import MESSAGES, judge
from voice_scale.pitch import detect
from voice_scale.scale import NOTE_SEC, base_frequency, build

NOTE_NAMES = ("ド", "ド#", "レ", "レ#", "ミ", "ファ", "ファ#", "ソ", "ソ#", "ラ", "ラ#", "シ")


def note_name(hz: float) -> str:
    """周波数を音名にする。A4=440Hz 基準。"""
    if not np.isfinite(hz) or hz <= 0:
        return "?"
    semitone = round(12.0 * np.log2(hz / 440.0)) + 57  # A4 を 57 とする
    return f"{NOTE_NAMES[semitone % 12]}{semitone // 12}"


def analyze(path: Path):
    """読み込み、無音を削り、音程を測る。"""
    raw = load(path)
    x = trim(raw)
    pitch = detect(x, SR)
    return x, pitch, judge(x, SR, pitch)


def cmd_info(args: argparse.Namespace) -> int:
    x, pitch, reasons = analyze(args.input)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    print(f"{args.input.name}")
    print(f"  長さ      {len(x) / SR:.2f} 秒")
    print(f"  ピーク    {peak:.3f}")
    print(f"  有声率    {pitch.voiced_ratio:.0%}  ({pitch.frames} 窓)")
    print(f"  ばらつき  {pitch.spread_cents:.0f} セント")
    if reasons:
        print("  判定      音階にできない")
        for r in reasons:
            print(f"            - {MESSAGES[r]}")
        return 1
    base, k = base_frequency(pitch.f0)
    print(f"  高さ      {pitch.f0:.1f} Hz  ({note_name(pitch.f0)})")
    print(f"  基準のド  {base:.1f} Hz  (C{4 + k})")
    print("  判定      音階にできる")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    x, pitch, reasons = analyze(args.input)
    if reasons:
        print(f"{args.input.name} は音階にできません", file=sys.stderr)
        for r in reasons:
            print(f"  {MESSAGES[r]}", file=sys.stderr)
        return 1

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    _, k = base_frequency(pitch.f0)
    print(f"{args.input.name}  {pitch.f0:.1f}Hz ({note_name(pitch.f0)})  基準 C{4 + k}")

    for name, wave in build(x, pitch.f0, SR, args.note_sec).items():
        write_wav(out_dir / f"{name}.wav", wave)
        print(f"  {name:5s} {len(wave) / SR:.3f}秒  {name}.wav")
    print(f"→ {out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="voice-scale", description="声から音階をつくる")
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="音の高さと判定を表示する")
    p_info.add_argument("input", type=Path)
    p_info.set_defaults(func=cmd_info)

    p_build = sub.add_parser("build", help="8音の WAV を書き出す")
    p_build.add_argument("input", type=Path)
    p_build.add_argument("-o", "--out", type=Path, default=Path("見本"))
    p_build.add_argument(
        "--note-sec",
        type=float,
        default=NOTE_SEC,
        help=f"1音の長さ[秒]。既定 {NOTE_SEC}（テンポ120の四分音符）",
    )
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    if not args.input.exists():
        print(f"見つかりません: {args.input}", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
