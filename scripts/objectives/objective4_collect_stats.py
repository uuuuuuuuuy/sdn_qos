#!/usr/bin/env python3
"""Objective 4 默认采集脚本。

该脚本聚焦 QoS 场景对比实验，内部调用通用的
``scripts/tools/export_metrics.py``，并预设了 Objective 4 常用
的端口/队列/Meter/流表轮询参数。使用者只需指定控制器地址、
涉及的交换机 DPID 及采样时间，就能生成论文需要的数据 CSV。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

_DEFAULT_MODULES = ("port", "queue", "meter", "flow")
_DEFAULT_SNAPSHOTS = ("topology-switches", "topology-links", "port-desc")


def _build_command(
    *,
    controller: str,
    dpids: Sequence[str],
    duration: int,
    interval: int,
    output: Path,
    prefix: str,
    modules: Sequence[str],
    snapshots: Sequence[str] | None,
    quiet: bool,
) -> List[str]:
    script = Path(__file__).resolve().parent.parent / "tools" / "export_metrics.py"
    cmd: List[str] = [sys.executable, str(script), "--controller", controller]

    for dpid in dpids:
        cmd.extend(("--dpid", dpid))

    for module in modules:
        cmd.extend(("--modules", module))

    cmd.extend(("--duration", str(duration)))
    cmd.extend(("--interval", str(interval)))

    cmd.extend(("--prefix", prefix, "--output", str(output)))

    if snapshots:
        for snapshot in snapshots:
            cmd.extend(("--snapshots", snapshot))

    if quiet:
        cmd.append("--quiet")

    return cmd


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Objective 4 QoS 采集脚本 (封装 export_metrics)",
    )
    parser.add_argument(
        "--controller",
        default="http://127.0.0.1:8080",
        help="FlowManager REST 控制器地址 (默认: %(default)s)",
    )
    parser.add_argument(
        "--dpid",
        dest="dpids",
        action="append",
        required=True,
        help="需要采集的交换机 DPID，可重复指定多台",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=180,
        help="采集持续时间 (秒)。为 0 时仅采集一次",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="轮询周期 (秒)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/objectives/data"),
        help="输出目录 (默认: %(default)s)",
    )
    parser.add_argument(
        "--prefix",
        default="objective4",
        help="生成 CSV 的文件名前缀",
    )
    parser.add_argument(
        "--modules",
        nargs="+",
        default=_DEFAULT_MODULES,
        help="采集的统计模块，默认覆盖端口/队列/Meter/流表",
    )
    parser.add_argument(
        "--snapshots",
        nargs="+",
        default=list(_DEFAULT_SNAPSHOTS),
        help="是否额外导出拓扑/端口描述快照",
    )
    parser.add_argument(
        "--no-snapshots",
        action="store_true",
        help="跳过拓扑快照导出",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="安静模式，仅输出必要提示",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    snapshots = [] if args.no_snapshots else list(args.snapshots or [])
    cmd = _build_command(
        controller=args.controller,
        dpids=tuple(args.dpids),
        duration=args.duration,
        interval=args.interval,
        output=args.output,
        prefix=args.prefix,
        modules=tuple(args.modules),
        snapshots=tuple(snapshots) if snapshots else None,
        quiet=args.quiet,
    )

    completed = subprocess.run(cmd, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
