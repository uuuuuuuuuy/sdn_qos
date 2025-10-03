#!/usr/bin/env python3
"""Objective 5 报告素材汇总脚本。

该脚本用于在整理阶段批量生成对比图表，并可选将 CSV 与图像打包。
内部通过调用 ``scripts/tools/plot_metrics.py`` 完成图表渲染，支持
直接复用 Objective 3/4 采集到的多组数据前缀。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Iterable, List, Mapping

_DEFAULT_CHART_FLAGS: Mapping[str, str] = {
    "port": "--no-port",
    "queue": "--no-queue",
    "meter": "--no-meter",
    "group": "--no-group",
    "table": "--no-table",
    "flow": "--no-flow",
    "qos": "--no-qos",
}


def _build_plot_command(
    *,
    runs: Mapping[str, str],
    output_dir: Path,
    figure_format: str,
    dpi: int,
    dpids: Iterable[int] | None,
    ports: Iterable[int] | None,
    topn: int,
    title_prefix: str,
    charts: Iterable[str],
) -> List[str]:
    script = Path(__file__).resolve().parent.parent / "tools" / "plot_metrics.py"
    cmd: List[str] = [sys.executable, str(script)]

    for label, prefix in runs.items():
        cmd.extend(("--run", f"{label}={prefix}"))

    cmd.extend(("--output-dir", str(output_dir)))
    cmd.extend(("--figure-format", figure_format))
    cmd.extend(("--dpi", str(dpi)))
    cmd.extend(("--topn-flows", str(topn)))
    if title_prefix:
        cmd.extend(("--title-prefix", title_prefix))

    if dpids:
        for dpid in dpids:
            cmd.extend(("--dpids", str(dpid)))
    if ports:
        for port in ports:
            cmd.extend(("--ports", str(port)))

    disabled = {name for name in _DEFAULT_CHART_FLAGS} - set(charts)
    for name in sorted(disabled):
        cmd.append(_DEFAULT_CHART_FLAGS[name])

    return cmd


def _parse_runs(items: Iterable[str]) -> Mapping[str, str]:
    runs: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--series 参数需要使用 label=prefix 形式：{item}")
        label, prefix = item.split("=", 1)
        runs[label] = prefix
    return runs


def _iter_prefix_files(prefix: str) -> Iterable[Path]:
    path = Path(prefix)
    if path.is_dir():
        # 遍历目录下的 CSV 文件
        yield from sorted(path.glob("*.csv"))
        return

    stem = path.stem if path.suffix else path.name
    directory = path.parent if path.parent != Path("") else Path(".")
    pattern = f"{stem}_*.csv"
    yield from sorted(directory.glob(pattern))


def _add_to_archive(archive: zipfile.ZipFile, base_dir: Path, path: Path) -> None:
    try:
        arcname = path.relative_to(base_dir)
    except ValueError:
        arcname = path.name
    archive.write(path, arcname)


def _create_archive(
    *,
    archive_path: Path,
    figure_dir: Path,
    prefixes: Iterable[str],
) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        base_dir = figure_dir.parent
        for file_path in sorted(figure_dir.rglob("*")):
            if file_path.is_file():
                _add_to_archive(bundle, base_dir, file_path)
        for prefix in prefixes:
            for csv_file in _iter_prefix_files(prefix):
                if csv_file.exists():
                    _add_to_archive(bundle, base_dir, csv_file)
        template = Path("docs/objectives/OBJECTIVE5_REPORT_TEMPLATE.md")
        if template.exists():
            _add_to_archive(bundle, base_dir, template)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Objective 5 报告素材脚本 (封装 plot_metrics)",
    )
    parser.add_argument(
        "--series",
        action="append",
        metavar="LABEL=PREFIX",
        required=True,
        help="实验标识及 CSV 前缀，例如 priority=docs/objectives/data/priority_run",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/objectives/figures"),
        help="图像输出目录 (默认: %(default)s)",
    )
    parser.add_argument(
        "--figure-format",
        default="png",
        help="输出图片格式 (默认: %(default)s)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="输出分辨率 DPI",
    )
    parser.add_argument(
        "--dpids",
        type=int,
        nargs="*",
        help="仅绘制指定交换机 DPID",
    )
    parser.add_argument(
        "--ports",
        type=int,
        nargs="*",
        help="仅绘制指定端口",
    )
    parser.add_argument(
        "--topn-flows",
        type=int,
        default=8,
        help="流表 Top-N 数量 (默认: %(default)s)",
    )
    parser.add_argument(
        "--title-prefix",
        default="",
        help="附加在所有图表标题前的文本",
    )
    parser.add_argument(
        "--charts",
        nargs="+",
        default=list(_DEFAULT_CHART_FLAGS.keys()),
        help="要保留的图表类别，可从 port/queue/meter/group/table/flow/qos 中选择",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        help="可选：生成包含图像与 CSV 的 zip 文件路径",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="安静模式，仅输出必要提示",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    runs = _parse_runs(args.series)
    charts = [name.lower() for name in args.charts]
    cmd = _build_plot_command(
        runs=runs,
        output_dir=args.output_dir,
        figure_format=args.figure_format,
        dpi=args.dpi,
        dpids=tuple(args.dpids) if args.dpids else None,
        ports=tuple(args.ports) if args.ports else None,
        topn=args.topn_flows,
        title_prefix=args.title_prefix,
        charts=charts,
    )

    if not args.quiet:
        print("[INFO] 正在生成图表...")
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        return completed.returncode

    if args.archive:
        if not args.quiet:
            print(f"[INFO] 打包图像与 CSV 至 {args.archive}")
        _create_archive(
            archive_path=args.archive,
            figure_dir=args.output_dir,
            prefixes=runs.values(),
        )

    if not args.quiet:
        print("[INFO] Objective 5 素材生成完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
