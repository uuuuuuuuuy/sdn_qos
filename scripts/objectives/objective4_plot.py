#!/usr/bin/env python3
"""Objective 4 专用绘图封装。

通过调用 ``scripts/tools/plot_metrics.py``，针对 Objective 4
的基线 vs 优先级/分类方案对比自动生成常见的吞吐与队列趋势图。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

_DEFAULT_CHARTS = (
    "port",
    "queue",
    "meter",
    "group",
    "table",
    "flow",
    "qos",
)


_DEF_CHART_FLAGS = {
    "port": "--no-port",
    "queue": "--no-queue",
    "meter": "--no-meter",
    "group": "--no-group",
    "table": "--no-table",
    "flow": "--no-flow",
    "qos": "--no-qos",
}


def _build_command(
    *,
    runs: Sequence[str],
    output: Path,
    charts: Sequence[str],
    ports: Sequence[int] | None,
    dpids: Sequence[int] | None,
    topn_flows: int | None,
    title_prefix: str | None,
    figure_format: str | None,
    dpi: int | None,
    quiet: bool,
) -> List[str]:
    script = Path(__file__).resolve().parent.parent / "tools" / "plot_metrics.py"
    cmd: List[str] = [sys.executable, str(script)]

    for item in runs:
        cmd.extend(("--run", item))

    cmd.extend(("--output-dir", str(output)))

    if figure_format:
        cmd.extend(("--figure-format", figure_format))
    if dpi:
        cmd.extend(("--dpi", str(dpi)))
    if ports:
        cmd.append("--ports")
        cmd.extend(str(port) for port in ports)
    if dpids:
        cmd.append("--dpids")
        cmd.extend(str(dpid) for dpid in dpids)
    if topn_flows is not None:
        cmd.extend(("--topn-flows", str(topn_flows)))
    if title_prefix:
        cmd.extend(("--title-prefix", title_prefix))

    disabled = {name for name in _DEF_CHART_FLAGS if name not in charts}
    for name in disabled:
        cmd.append(_DEF_CHART_FLAGS[name])

    if quiet:
        cmd.append("--quiet")

    return cmd


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Objective 4 绘图脚本 (封装 plot_metrics)",
    )
    parser.add_argument(
        "--series",
        action="append",
        metavar="LABEL=PREFIX",
        required=True,
        help="实验系列，格式为 标签=CSV前缀，例：priority=docs/objectives/data/priority_run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/objectives/figures/qos_comparison"),
        help="图像输出目录 (默认: %(default)s)",
    )
    parser.add_argument(
        "--charts",
        nargs="+",
        choices=tuple(_DEF_CHART_FLAGS.keys()),
        default=list(_DEFAULT_CHARTS),
        help="需要生成的图表类别 (默认: %(default)s)",
    )
    parser.add_argument(
        "--ports",
        type=int,
        nargs="+",
        help="关注的端口号 (可多值)",
    )
    parser.add_argument(
        "--dpids",
        type=int,
        nargs="+",
        help="关注的交换机 DPID (可多值)",
    )
    parser.add_argument(
        "--topn-flows",
        type=int,
        default=6,
        help="每台交换机显示的流表 Top-N 数量 (默认: %(default)s)",
    )
    parser.add_argument(
        "--title-prefix",
        help="为所有图表添加统一标题前缀",
    )
    parser.add_argument(
        "--figure-format",
        default="png",
        help="输出图像格式 (默认: %(default)s)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=144,
        help="输出分辨率 DPI (默认: %(default)s)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="安静模式，仅输出必要提示",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    cmd = _build_command(
        runs=tuple(args.series),
        output=args.output,
        charts=tuple(args.charts),
        ports=tuple(args.ports) if args.ports else None,
        dpids=tuple(args.dpids) if args.dpids else None,
        topn_flows=args.topn_flows,
        title_prefix=args.title_prefix,
        figure_format=args.figure_format,
        dpi=args.dpi,
        quiet=args.quiet,
    )

    completed = subprocess.run(cmd, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
