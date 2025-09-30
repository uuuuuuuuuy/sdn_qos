#!/usr/bin/env python3
"""批量采集 Ryu REST 接口统计信息并导出为 CSV。

示例：
    python scripts/objectives/objective4_collect_stats.py \
        --controller http://127.0.0.1:8080 \
        --dpid 1 --dpid 2 --duration 120 --interval 5 \
        --prefix priority_run --output docs/objectives/data
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Mapping

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="通过 Ryu ofctl REST 接口周期性抓取端口/流统计，并输出 CSV 文件。"
    )
    parser.add_argument(
        "--controller",
        default="http://127.0.0.1:8080",
        help="Ryu 控制器 REST 服务地址（默认：http://127.0.0.1:8080）",
    )
    parser.add_argument(
        "--dpid",
        action="append",
        dest="dpids",
        type=int,
        required=True,
        help="需要采集的交换机 DPID（十进制），可重复指定多次。",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="两次采集之间的间隔秒数（默认 5 秒）。",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="采集总时长（秒），默认 60 秒。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/objectives/data"),
        help="CSV 输出目录，将自动创建（默认 docs/objectives/data）。",
    )
    parser.add_argument(
        "--prefix",
        default="experiment",
        help="输出文件名前缀，例如 priority_run（默认 experiment）。",
    )
    parser.add_argument(
        "--flow-stats",
        action="store_true",
        help="同时导出流表统计（默认只导出端口统计）。",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="启动前先访问一次控制器，失败时立即退出。",
    )
    return parser.parse_args()


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def request_json(url: str) -> Mapping[str, object]:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, Mapping):
        raise ValueError(f"Unexpected response from {url}: {data!r}")
    return data


def collect_port_rows(base: str, dpids: Iterable[int]) -> List[List[object]]:
    rows: List[List[object]] = []
    now = timestamp()
    for dpid in dpids:
        url = f"{base}/stats/port/{dpid}"
        payload = request_json(url)
        entries = payload.get(str(dpid), [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            rows.append(
                [
                    now,
                    dpid,
                    entry.get("port_no"),
                    entry.get("rx_packets"),
                    entry.get("tx_packets"),
                    entry.get("rx_bytes"),
                    entry.get("tx_bytes"),
                    entry.get("rx_dropped"),
                    entry.get("tx_dropped"),
                    entry.get("rx_errors"),
                    entry.get("tx_errors"),
                ]
            )
    return rows


def collect_flow_rows(base: str, dpids: Iterable[int]) -> List[List[object]]:
    rows: List[List[object]] = []
    now = timestamp()
    for dpid in dpids:
        url = f"{base}/stats/flow/{dpid}"
        payload = request_json(url)
        entries = payload.get(str(dpid), [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            match = json.dumps(entry.get("match", {}), ensure_ascii=False, sort_keys=True)
            actions = json.dumps(entry.get("instructions", {}), ensure_ascii=False)
            rows.append(
                [
                    now,
                    dpid,
                    entry.get("table_id"),
                    entry.get("priority"),
                    entry.get("cookie"),
                    match,
                    actions,
                    entry.get("packet_count"),
                    entry.get("byte_count"),
                    entry.get("duration_sec"),
                ]
            )
    return rows


def main() -> int:
    args = parse_args()
    base = args.controller.rstrip("/")

    args.output.mkdir(parents=True, exist_ok=True)

    if args.verify:
        try:
            request_json(f"{base}/stats/switches")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"控制器 {base} 无法访问：{exc}", file=sys.stderr)
            return 1

    port_file = args.output / f"{args.prefix}_ports.csv"
    flow_file = args.output / f"{args.prefix}_flows.csv"

    with port_file.open("w", newline="", encoding="utf-8") as pf:
        port_writer = csv.writer(pf)
        port_writer.writerow(
            [
                "timestamp",
                "dpid",
                "port_no",
                "rx_packets",
                "tx_packets",
                "rx_bytes",
                "tx_bytes",
                "rx_dropped",
                "tx_dropped",
                "rx_errors",
                "tx_errors",
            ]
        )
        if args.flow_stats:
            ff = flow_file.open("w", newline="", encoding="utf-8")
            flow_writer = csv.writer(ff)
            flow_writer.writerow(
                [
                    "timestamp",
                    "dpid",
                    "table_id",
                    "priority",
                    "cookie",
                    "match",
                    "instructions",
                    "packet_count",
                    "byte_count",
                    "duration_sec",
                ]
            )
        else:
            ff = None
            flow_writer = None

        try:
            start = time.time()
            while time.time() - start <= args.duration:
                port_rows = collect_port_rows(base, args.dpids)
                for row in port_rows:
                    port_writer.writerow(row)
                pf.flush()

                if flow_writer is not None:
                    flow_rows = collect_flow_rows(base, args.dpids)
                    for row in flow_rows:
                        flow_writer.writerow(row)
                    ff.flush()  # type: ignore[union-attr]

                time.sleep(args.interval)
        finally:
            if ff is not None:
                ff.close()

    print(f"端口统计已保存至 {port_file}")
    if args.flow_stats:
        print(f"流表统计已保存至 {flow_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
