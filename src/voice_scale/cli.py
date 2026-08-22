"""できあがった音階を測って表示する。

    voice-scale check 見本/にゃー

音をつくるのは `node tools/generate.mjs`。こちらはその結果を確かめる係。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voice_scale.measure import Measured, interval_errors, measure_scale

MAX_INTERVAL_CENTS = 15.0  # これを超えると音階として狂って聞こえる
MAX_TAIL = 0.01  # 鳴り終わりの振幅。大きいとプチッと鳴る


def 判定(measured: list[Measured], errors: dict[str, float]) -> list[str]:
    """おかしいところを並べて返す。空なら問題なし。"""
    problems = []

    狂い = {name: round(c, 1) for name, c in errors.items() if abs(c) > MAX_INTERVAL_CENTS}
    if 狂い:
        problems.append(f"音程が狂っている: {狂い}")

    lengths = {m.sec for m in measured}
    if len(lengths) > 1:
        problems.append(f"長さがそろっていない: {sorted(lengths)}")

    切れ = [m.file for m in measured if m.tail > MAX_TAIL]
    if 切れ:
        problems.append(f"鳴り終わりがプチッと切れる: {' '.join(切れ)}")

    形式 = {(m.channels, m.sample_rate, m.bit_depth) for m in measured}
    if 形式 != {(1, 44100, 16)}:
        problems.append(f"Scratch が読める形式でない: {形式}")

    return problems


def cmd_check(args: argparse.Namespace) -> int:
    measured = measure_scale(args.directory)
    errors = interval_errors(measured)

    print(f"{args.directory}")
    列 = ["音", "ファイル", "Hz", "音程の狂い", "鳴っている長さ", "鳴り終わり"]
    print(f"  {列[0]:6s}{列[1]:10s}{列[2]:>9}{列[3]:>12}{列[4]:>14}{列[5]:>11}")
    for m in measured:
        print(
            f"  {m.name:6s}{m.file:10s}{m.hz:9.1f}{errors[m.name]:+10.1f}ct"
            f"{m.sounding_sec:12.3f}秒{m.tail:11.4f}"
        )

    problems = 判定(measured, errors)
    print()
    if problems:
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        return 1
    print(
        f"  ○ 8音とも {measured[0].sec:.3f}秒、モノラル16bit 44100Hz、音程の狂いは"
        f" {max(abs(c) for c in errors.values()):.1f}セント以内"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="voice-scale", description="できあがった音階を測る")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="8音の WAV を測って確かめる")
    p_check.add_argument("directory", type=Path)
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    if not args.directory.is_dir():
        print(f"見つかりません: {args.directory}", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
