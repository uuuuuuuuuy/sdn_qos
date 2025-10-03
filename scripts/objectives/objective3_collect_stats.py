#!/usr/bin/env python3
"""Objective 3 QoS 配置校验采集脚本。

本脚本用于在 FlowManager 中切换不同 QoS 策略后，快速抓取端口、
流表与 QoS 队列/规则等关键指标。它会在每个场景开始采集前提示
确认，便于在 Web UI 中完成配置、启动流量，再由脚本调用
``scripts/tools/export_metrics.py`` 生成对应的 CSV 数据。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

_DEFAULT_SCENARIOS = ("baseline", "priority")
_DEFAULT_MODULES = ("port", "flow", "queue", "qos-queue", "qos-rule")
_DEFAULT_SNAPSHOTS = ("port-desc",)


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

    if duration:
        cmd.extend(("--duration", str(duration)))
    else:
        cmd.extend(("--samples", "1"))

    cmd.extend(("--interval", str(interval)))
    cmd.extend(("--prefix", prefix, "--output", str(output)))

    if snapshots:
        for snapshot in snapshots:
            cmd.extend(("--snapshots", snapshot))

    if quiet:
        cmd.append("--quiet")

    return cmd


def _prompt(message: str) -> None:
    try:
        input(message)
    except EOFError:
        # 在非交互环境中继续执行
        pass


def _prepare_scenarios(raw: Sequence[str] | None) -> Sequence[str]:
    if not raw:
        return _DEFAULT_SCENARIOS
    ordered: List[str] = []
    seen: set[str] = set()
    for item in raw:
        name = item.strip()
        if not name or name in seen:
            continue
        ordered.append(name)
        seen.add(name)
    return ordered or _DEFAULT_SCENARIOS


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Objective 3 QoS 采集脚本 (封装 export_metrics)",
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
        default=120,
        help="单个场景的采集持续时间 (秒)，0 表示只采集一次",
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
        default="objective3",
        help="生成 CSV 的基础前缀，实际输出会追加场景名",
    )
    parser.add_argument(
        "--scenario",
        dest="scenarios",
        action="append",
        help="采集的场景标识 (默认: baseline, priority)",
    )
    parser.add_argument(
        "--modules",
        nargs="+",
        default=_DEFAULT_MODULES,
        help="采集的统计模块",
    )
    parser.add_argument(
        "--snapshots",
        nargs="+",
        default=list(_DEFAULT_SNAPSHOTS),
        help="额外导出的快照模块",
    )
    parser.add_argument(
        "--no-snapshots",
        action="store_true",
        help="跳过快照导出",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="安静模式，仅输出必要提示",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="禁用场景开始前的等待提示",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    snapshots = [] if args.no_snapshots else list(args.snapshots or [])
    scenarios = _prepare_scenarios(args.scenarios)

    for scenario in scenarios:
        if not args.non_interactive:
            _prompt(
                f"\n请在 FlowManager 中切换至 '{scenario}' 策略并启动流量，按 Enter 开始采集..."
            )
        scenario_prefix = f"{args.prefix}_{scenario}" if args.prefix else scenario
        cmd = _build_command(
            controller=args.controller,
            dpids=tuple(args.dpids),
            duration=args.duration,
            interval=args.interval,
            output=args.output,
            prefix=scenario_prefix,
            modules=tuple(args.modules),
            snapshots=tuple(snapshots) if snapshots else None,
            quiet=args.quiet,
        )
        print(f"[INFO] 开始采集场景 {scenario}，输出前缀：{scenario_prefix}")
        completed = subprocess.run(cmd, check=False)
        if completed.returncode != 0:
            return completed.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
