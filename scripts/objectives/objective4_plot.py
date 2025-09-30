#!/usr/bin/env python3
"""根据 CSV 统计绘制带宽对比图。

示例：
    python scripts/objectives/objective4_plot.py \
        --series baseline=docs/objectives/data/baseline_ports.csv \
        --series priority=docs/objectives/data/priority_ports.csv \
        --port 2 --metric tx_mbps \
        --output docs/objectives/data/priority_vs_baseline.png
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd

SUPPORTED_METRICS = {"tx_mbps", "rx_mbps"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="读取端口统计 CSV 并绘制吞吐对比图。")
    parser.add_argument(
        "--series",
        action="append",
        required=True,
        metavar="LABEL=CSV",
        help="需要对比的序列，格式为 名称=CSV路径，可指定多次。",
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="计算吞吐量的端口号，例如 2。",
    )
    parser.add_argument(
        "--metric",
        choices=sorted(SUPPORTED_METRICS),
        default="tx_mbps",
        help="绘图指标，支持 tx_mbps（发送）或 rx_mbps（接收）。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="输出图片路径（PNG/SVG 等），父目录会自动创建。",
    )
    parser.add_argument(
        "--title",
        default="Port Throughput Comparison",
        help="图表标题，可选。",
    )
    return parser.parse_args()


def load_series(series_args: List[str]) -> Dict[str, pd.DataFrame]:
    series: Dict[str, pd.DataFrame] = {}
    for item in series_args:
        if "=" not in item:
            raise ValueError(f"--series 参数格式错误：{item}")
        label, path = item.split("=", 1)
        csv_path = Path(path)
        if not csv_path.exists():
            raise FileNotFoundError(f"找不到 CSV 文件：{csv_path}")
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        df.sort_values("timestamp", inplace=True)
        series[label] = df
    return series


def compute_metric(df: pd.DataFrame, metric: str, port: int) -> pd.DataFrame:
    filtered = df[df["port_no"] == port].copy()
    if filtered.empty:
        raise ValueError(f"CSV 中未包含端口 {port} 的统计数据。")
    filtered.sort_values("timestamp", inplace=True)
    filtered["timestamp"] = pd.to_datetime(filtered["timestamp"])
    filtered["delta_seconds"] = filtered["timestamp"].diff().dt.total_seconds()
    if metric == "tx_mbps":
        filtered[metric] = filtered["tx_bytes"].diff() * 8 / (filtered["delta_seconds"] * 1_000_000)
    else:
        filtered[metric] = filtered["rx_bytes"].diff() * 8 / (filtered["delta_seconds"] * 1_000_000)
    filtered.loc[filtered["delta_seconds"] <= 0, metric] = None
    filtered.dropna(subset=[metric], inplace=True)
    return filtered


def main() -> int:
    args = parse_args()
    series = load_series(args.series)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 5))
    for label, df in series.items():
        processed = compute_metric(df, args.metric, args.port)
        plt.plot(processed["timestamp"], processed[args.metric], marker="o", label=label)

    plt.title(args.title)
    plt.xlabel("时间")
    plt.ylabel("Mbps")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(args.output)
    print(f"图表已保存至 {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
