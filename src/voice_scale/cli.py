"""コマンドライン。見本音源をつくるときに使う。

ブラウザ側の入り口は docs/app.js。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NamedTuple

import numpy as np

from voice_scale import wav
from voice_scale.audio import OUT_SR, trim
from voice_scale.check import MESSAGES, judge
from voice_scale.pitch import Pitch, detect
from voice_scale.scale import NOTE_SEC, base_frequency, build, nearest_note

NOTE_NAMES = ("ド", "ド#", "レ", "レ#", "ミ", "ファ", "ファ#", "ソ", "ソ#", "ラ", "ラ#", "シ")


def note_name(hz: float) -> str:
    """周波数を音名にする。A4=440Hz 基準。"""
    if not np.isfinite(hz) or hz <= 0:
        return "?"
    semitone = round(12.0 * np.log2(hz / 440.0)) + 57  # A4 を 57 とする
    return f"{NOTE_NAMES[semitone % 12]}{semitone // 12}"


class Analysis(NamedTuple):
    """読み込みから判定までの結果をまとめたもの。"""

    wave: np.ndarray
    pitch: Pitch
    reasons: list[str]


def analyze(path: Path) -> Analysis:
    """読み込み、無音を削り、音程を測り、音階にできるか判定する。"""
    wave = trim(wav.load(path))
    pitch = detect(wave, OUT_SR)
    return Analysis(wave, pitch, judge(wave, OUT_SR, pitch))


def cmd_info(args: argparse.Namespace) -> int:
    wave, pitch, reasons = analyze(args.input)
    peak = float(np.max(np.abs(wave))) if len(wave) else 0.0
    print(f"{args.input.name}")
    print(f"  長さ      {len(wave) / OUT_SR:.2f} 秒")
    print(f"  ピーク    {peak:.3f}")
    print(f"  有声率    {pitch.voiced_ratio:.0%}  ({pitch.frames} 窓)")
    print(f"  ばらつき  {pitch.spread_cents:.0f} セント")
    if reasons:
        print("  判定      音階にできない")
        for reason in reasons:
            print(f"            - {MESSAGES[reason]}")
        return 1
    base = base_frequency(pitch.f0)
    near = nearest_note(pitch.f0)
    print(f"  高さ      {pitch.f0:.1f} Hz  ({note_name(pitch.f0)})")
    print(f"  近い音    {near.name}  ({near.cents:+.0f} セント)")
    print(f"  基準のド  {base.hz:.1f} Hz  (C{4 + base.octave})")
    print("  判定      音階にできる")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    wave, pitch, reasons = analyze(args.input)
    if reasons:
        print(f"{args.input.name} は音階にできません", file=sys.stderr)
        for reason in reasons:
            print(f"  {MESSAGES[reason]}", file=sys.stderr)
        return 1

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    base = base_frequency(pitch.f0)
    print(f"{args.input.name}  {pitch.f0:.1f}Hz ({note_name(pitch.f0)})  基準 C{4 + base.octave}")

    for sound in build(wave, pitch.f0, OUT_SR, args.note_sec):
        wav.write(out_dir / f"{sound.name}.wav", sound.samples)
        print(f"  {sound.name:5s} {len(sound.samples) / OUT_SR:.3f}秒  {sound.name}.wav")
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
