#!/usr/bin/env python3
"""FlowManager 场景通用统计导出脚本。

该脚本覆盖项目 Objective 1-5 的常见采集需求，可根据所选模块：

* 周期性抓取端口 / 队列 / 流表 / Meter / Group / Table / QoS 队列 & 规则等统计。
* 按需导出拓扑（交换机 / 主机 / 链路）与端口描述快照，适用于论文附录。

示例 1：Objective 2 连通性验证，仅采集端口吞吐三次。
    python scripts/objectives/objective4_collect_stats.py \
        --controller http://127.0.0.1:8080 \
        --dpid 1 --dpid 2 --dpid 3 \
        --modules port --samples 3 --interval 2 \
        --prefix obj2_smoke --output docs/objectives/data

示例 2：Objective 3-4 QoS 对比，导出多项统计并保存拓扑快照。
    python scripts/objectives/objective4_collect_stats.py \
        --controller http://127.0.0.1:8080 \
        --dpid 1 --dpid 2 --dpid 3 \
        --modules port flow queue meter table qos-queue qos-rule \
        --snapshots topology-switches topology-links topology-hosts port-desc \
        --duration 180 --interval 5 \
        --prefix priority_run --output docs/objectives/data
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Mapping, MutableMapping, Sequence, TextIO

import requests

REQUEST_TIMEOUT = 10.0


@dataclass(frozen=True)
class ModuleDefinition:
    """周期采样模块定义。"""

    file_suffix: str
    headers: Sequence[str]
    collector: Callable[[str, Sequence[int], str], Iterable[Sequence[object]]]
    requires_dpids: bool = True


@dataclass(frozen=True)
class SnapshotDefinition:
    """快照模块定义。"""

    file_suffix: str
    headers: Sequence[str]
    collector: Callable[[str, Sequence[int], str], Iterable[Sequence[object]]]
    requires_dpids: bool = False


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def request_json(url: str) -> Mapping[str, object]:
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, Mapping) and not isinstance(data, list):
        raise ValueError(f"Unexpected response from {url}: {data!r}")
    if isinstance(data, list):
        return {"items": data}
    return data


def safe_request(url: str) -> Mapping[str, object]:
    try:
        return request_json(url)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[WARN] 请求 {url} 失败：{exc}", file=sys.stderr)
        return {}


def collect_port_rows(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/stats/port/{dpid}"
        payload = safe_request(url)
        entries = payload.get(str(dpid), []) if isinstance(payload, Mapping) else []
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


def collect_flow_rows(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/stats/flow/{dpid}"
        payload = safe_request(url)
        entries = payload.get(str(dpid), []) if isinstance(payload, Mapping) else []
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
                    entry.get("duration_nsec"),
                ]
            )
    return rows


def collect_queue_rows(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/stats/queue/{dpid}"
        payload = safe_request(url)
        entries = payload.get(str(dpid), []) if isinstance(payload, Mapping) else []
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
                    entry.get("queue_id"),
                    entry.get("tx_bytes"),
                    entry.get("tx_packets"),
                    entry.get("tx_errors"),
                    entry.get("duration_sec"),
                    entry.get("duration_nsec"),
                ]
            )
    return rows


def collect_meter_rows(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/stats/meter/{dpid}"
        payload = safe_request(url)
        entries = payload.get(str(dpid), []) if isinstance(payload, Mapping) else []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            band_stats = json.dumps(entry.get("band_stats", entry.get("bands", [])), ensure_ascii=False)
            rows.append(
                [
                    now,
                    dpid,
                    entry.get("meter_id"),
                    entry.get("flow_count"),
                    entry.get("packet_in_count"),
                    entry.get("byte_in_count"),
                    entry.get("duration_sec"),
                    entry.get("duration_nsec"),
                    band_stats,
                ]
            )
    return rows


def collect_table_rows(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/stats/table/{dpid}"
        payload = safe_request(url)
        entries = payload.get(str(dpid), []) if isinstance(payload, Mapping) else []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            rows.append(
                [
                    now,
                    dpid,
                    entry.get("table_id"),
                    entry.get("active_count"),
                    entry.get("lookup_count"),
                    entry.get("matched_count"),
                    entry.get("max_entries"),
                    entry.get("duration_sec"),
                    entry.get("duration_nsec"),
                ]
            )
    return rows


def collect_group_rows(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/stats/group/{dpid}"
        payload = safe_request(url)
        entries = payload.get(str(dpid), []) if isinstance(payload, Mapping) else []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            bucket_stats = json.dumps(entry.get("bucket_stats", []), ensure_ascii=False)
            rows.append(
                [
                    now,
                    dpid,
                    entry.get("group_id"),
                    entry.get("ref_count"),
                    entry.get("packet_count"),
                    entry.get("byte_count"),
                    entry.get("duration_sec"),
                    entry.get("duration_nsec"),
                    bucket_stats,
                ]
            )
    return rows


def collect_qos_queue_rows(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/qos/queue/{dpid}"
        payload = safe_request(url)
        items = payload.get("items") if isinstance(payload, Mapping) else None
        if not isinstance(items, list):
            continue
        for port_entry in items:
            if not isinstance(port_entry, Mapping):
                continue
            port_name = port_entry.get("port_name") or port_entry.get("port")
            port_no = port_entry.get("port_no")
            queues = port_entry.get("queues", [])
            if not isinstance(queues, list):
                continue
            for queue in queues:
                if not isinstance(queue, Mapping):
                    continue
                rows.append(
                    [
                        now,
                        dpid,
                        port_name,
                        port_no,
                        queue.get("queue_id") or queue.get("id"),
                        queue.get("type"),
                        queue.get("min_rate"),
                        queue.get("max_rate"),
                        queue.get("burst"),
                        queue.get("priority"),
                    ]
                )
    return rows


def collect_qos_rule_rows(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/qos/rules/{dpid}"
        payload = safe_request(url)
        items = payload.get("items") if isinstance(payload, Mapping) else None
        if not isinstance(items, list):
            continue
        for rule in items:
            if not isinstance(rule, Mapping):
                continue
            match = json.dumps(rule.get("match", {}), ensure_ascii=False, sort_keys=True)
            actions = json.dumps(rule.get("actions", {}), ensure_ascii=False)
            rows.append(
                [
                    now,
                    dpid,
                    rule.get("id"),
                    rule.get("priority"),
                    rule.get("queue"),
                    match,
                    actions,
                    rule.get("hard_timeout"),
                    rule.get("idle_timeout"),
                ]
            )
    return rows


def snapshot_topology_switches(base: str, _dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    url = f"{base}/v1.0/topology/switches"
    payload = safe_request(url)
    items = payload.get("items") if isinstance(payload, Mapping) else None
    rows: List[Sequence[object]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, Mapping):
                continue
            dpid = item.get("dpid")
            ports = item.get("ports", [])
            if not isinstance(ports, list):
                rows.append([now, dpid, None, None, None])
                continue
            for port in ports:
                if not isinstance(port, Mapping):
                    continue
                rows.append(
                    [
                        now,
                        dpid,
                        port.get("port_no"),
                        port.get("name"),
                        port.get("hw_addr"),
                    ]
                )
    return rows


def snapshot_topology_links(base: str, _dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    url = f"{base}/v1.0/topology/links"
    payload = safe_request(url)
    items = payload.get("items") if isinstance(payload, Mapping) else None
    rows: List[Sequence[object]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, Mapping):
                continue
            src = item.get("src", {}) if isinstance(item.get("src"), Mapping) else {}
            dst = item.get("dst", {}) if isinstance(item.get("dst"), Mapping) else {}
            rows.append(
                [
                    now,
                    src.get("dpid"),
                    src.get("port_no"),
                    dst.get("dpid"),
                    dst.get("port_no"),
                    item.get("link_id"),
                ]
            )
    return rows


def snapshot_topology_hosts(base: str, _dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    url = f"{base}/v1.0/topology/hosts"
    payload = safe_request(url)
    items = payload.get("items") if isinstance(payload, Mapping) else None
    rows: List[Sequence[object]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, Mapping):
                continue
            port = item.get("port", {}) if isinstance(item.get("port"), Mapping) else {}
            rows.append(
                [
                    now,
                    item.get("mac"),
                    ",".join(item.get("ipv4", []) or []),
                    ",".join(item.get("ipv6", []) or []),
                    port.get("dpid"),
                    port.get("port_no"),
                ]
            )
    return rows


def snapshot_port_desc(base: str, dpids: Sequence[int], now: str) -> Iterable[Sequence[object]]:
    rows: List[Sequence[object]] = []
    for dpid in dpids:
        url = f"{base}/stats/portdesc/{dpid}"
        payload = safe_request(url)
        entries = payload.get(str(dpid), []) if isinstance(payload, Mapping) else []
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
                    entry.get("name"),
                    entry.get("hw_addr"),
                    entry.get("state"),
                    entry.get("curr"),
                ]
            )
    return rows


TIME_SERIES_MODULES: MutableMapping[str, ModuleDefinition] = {
    "port": ModuleDefinition(
        file_suffix="ports",
        headers=[
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
        ],
        collector=collect_port_rows,
    ),
    "flow": ModuleDefinition(
        file_suffix="flows",
        headers=[
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
            "duration_nsec",
        ],
        collector=collect_flow_rows,
    ),
    "queue": ModuleDefinition(
        file_suffix="queues",
        headers=[
            "timestamp",
            "dpid",
            "port_no",
            "queue_id",
            "tx_bytes",
            "tx_packets",
            "tx_errors",
            "duration_sec",
            "duration_nsec",
        ],
        collector=collect_queue_rows,
    ),
    "meter": ModuleDefinition(
        file_suffix="meters",
        headers=[
            "timestamp",
            "dpid",
            "meter_id",
            "flow_count",
            "packet_in_count",
            "byte_in_count",
            "duration_sec",
            "duration_nsec",
            "band_stats",
        ],
        collector=collect_meter_rows,
    ),
    "table": ModuleDefinition(
        file_suffix="tables",
        headers=[
            "timestamp",
            "dpid",
            "table_id",
            "active_count",
            "lookup_count",
            "matched_count",
            "max_entries",
            "duration_sec",
            "duration_nsec",
        ],
        collector=collect_table_rows,
    ),
    "group": ModuleDefinition(
        file_suffix="groups",
        headers=[
            "timestamp",
            "dpid",
            "group_id",
            "ref_count",
            "packet_count",
            "byte_count",
            "duration_sec",
            "duration_nsec",
            "bucket_stats",
        ],
        collector=collect_group_rows,
    ),
    "qos-queue": ModuleDefinition(
        file_suffix="qos_queues",
        headers=[
            "timestamp",
            "dpid",
            "port_name",
            "port_no",
            "queue_id",
            "type",
            "min_rate",
            "max_rate",
            "burst",
            "priority",
        ],
        collector=collect_qos_queue_rows,
    ),
    "qos-rule": ModuleDefinition(
        file_suffix="qos_rules",
        headers=[
            "timestamp",
            "dpid",
            "rule_id",
            "priority",
            "queue",
            "match",
            "actions",
            "hard_timeout",
            "idle_timeout",
        ],
        collector=collect_qos_rule_rows,
    ),
}

SNAPSHOT_MODULES: MutableMapping[str, SnapshotDefinition] = {
    "topology-switches": SnapshotDefinition(
        file_suffix="topology_switches",
        headers=["timestamp", "dpid", "port_no", "name", "hw_addr"],
        collector=snapshot_topology_switches,
    ),
    "topology-links": SnapshotDefinition(
        file_suffix="topology_links",
        headers=["timestamp", "src_dpid", "src_port", "dst_dpid", "dst_port", "link_id"],
        collector=snapshot_topology_links,
    ),
    "topology-hosts": SnapshotDefinition(
        file_suffix="topology_hosts",
        headers=["timestamp", "mac", "ipv4", "ipv6", "attached_dpid", "attached_port"],
        collector=snapshot_topology_hosts,
    ),
    "port-desc": SnapshotDefinition(
        file_suffix="port_desc",
        headers=["timestamp", "dpid", "port_no", "name", "hw_addr", "state", "curr"],
        collector=snapshot_port_desc,
        requires_dpids=True,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="采集 FlowManager / Ryu 统计并导出 CSV，可跨 Objective 通用。"
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
        help="需要采集的交换机 DPID（十进制），可重复指定。",
    )
    parser.add_argument(
        "--modules",
        nargs="+",
        choices=sorted(TIME_SERIES_MODULES.keys()),
        default=["port"],
        help="需要周期采样的模块，默认仅采集端口统计。",
    )
    parser.add_argument(
        "--no-modules",
        action="store_true",
        help="仅导出快照，不做周期采样。",
    )
    parser.add_argument(
        "--snapshots",
        nargs="+",
        choices=sorted(SNAPSHOT_MODULES.keys()),
        default=[],
        help="额外导出的静态快照模块，例如 topology-switches。",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="两次采样之间的间隔秒数（默认 5 秒）。",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=60.0,
        help="采集总时长（秒），默认 60 秒。",
    )
    parser.add_argument(
        "--samples",
        type=int,
        help="采样次数上限（与 --duration 取最小值）。不指定时按时长计算。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/objectives/data"),
        help="输出目录，将自动创建（默认 docs/objectives/data）。",
    )
    parser.add_argument(
        "--prefix",
        default="experiment",
        help="输出文件名前缀，例如 priority_run（默认 experiment）。",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="启动前访问一次控制器的 /stats/switches，失败时立即退出。",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP 请求超时时间（秒），默认 10 秒。",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="降低输出噪声，仅打印最终结果。",
    )
    return parser.parse_args()


def ensure_dpids(args: argparse.Namespace, defs: Iterable[ModuleDefinition]) -> None:
    if args.dpids:
        return
    requires = any(defn.requires_dpids for defn in defs)
    if requires:
        raise SystemExit("当前选定的模块需要提供至少一个 --dpid。")


def open_csv_writers(
    output_dir: Path,
    prefix: str,
    modules: Iterable[ModuleDefinition],
) -> tuple[Mapping[str, csv.writer], Mapping[str, TextIO]]:
    writers: MutableMapping[str, csv.writer] = {}
    handles: MutableMapping[str, TextIO] = {}
    for module in modules:
        file_path = output_dir / f"{prefix}_{module.file_suffix}.csv"
        fh = file_path.open("w", newline="", encoding="utf-8")
        writer = csv.writer(fh)
        writer.writerow(module.headers)
        writers[module.file_suffix] = writer
        handles[module.file_suffix] = fh
    return writers, handles


def run_time_series(
    base: str,
    dpids: Sequence[int],
    modules: Sequence[ModuleDefinition],
    writers: Mapping[str, csv.writer],
    handles: Mapping[str, TextIO],
    interval: float,
    duration: float,
    samples_limit: int | None,
    quiet: bool,
) -> None:
    start = time.time()
    samples = 0
    while True:
        now = timestamp()
        for module in modules:
            rows = list(module.collector(base, dpids, now))
            writer = writers[module.file_suffix]
            for row in rows:
                writer.writerow(row)
            handle = handles.get(module.file_suffix)
            if handle is not None:
                handle.flush()
        samples += 1
        if not quiet:
            print(f"[{now}] 已完成第 {samples} 次采样。")
        if samples_limit is not None and samples >= samples_limit:
            break
        if duration <= 0:
            if samples_limit is None:
                break
        else:
            elapsed = time.time() - start
            if elapsed >= duration:
                break
        time.sleep(max(interval, 0))


def export_snapshots(
    base: str,
    dpids: Sequence[int],
    snapshots: Sequence[SnapshotDefinition],
    output_dir: Path,
    prefix: str,
    quiet: bool,
) -> None:
    now = timestamp()
    for snapshot in snapshots:
        rows = list(snapshot.collector(base, dpids, now))
        file_path = output_dir / f"{prefix}_{snapshot.file_suffix}.csv"
        with file_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(snapshot.headers)
            for row in rows:
                writer.writerow(row)
        if not quiet:
            print(f"快照 {snapshot.file_suffix} 已保存：{file_path}")


def main() -> int:
    args = parse_args()
    base = args.controller.rstrip("/")
    args.output.mkdir(parents=True, exist_ok=True)

    global REQUEST_TIMEOUT  # pylint: disable=global-statement
    REQUEST_TIMEOUT = args.timeout

    module_defs: List[ModuleDefinition]
    if args.no_modules:
        module_defs = []
    else:
        module_defs = [TIME_SERIES_MODULES[name] for name in args.modules]
    snapshot_defs = [SNAPSHOT_MODULES[name] for name in args.snapshots]

    ensure_dpids(args, module_defs + [snap for snap in snapshot_defs if snap.requires_dpids])

    if args.verify:
        try:
            request_json(f"{base}/stats/switches")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"控制器 {base} 无法访问：{exc}", file=sys.stderr)
            return 1

    if module_defs:
        writers, handles = open_csv_writers(args.output, args.prefix, module_defs)
        try:
            run_time_series(
                base=base,
                dpids=tuple(args.dpids or []),
                modules=module_defs,
                writers=writers,
                handles=handles,
                interval=args.interval,
                duration=args.duration,
                samples_limit=args.samples,
                quiet=args.quiet,
            )
        finally:
            for handle in handles.values():
                handle.close()
        if not args.quiet:
            for module in module_defs:
                print(
                    f"周期统计 {module.file_suffix} 已保存至 "
                    f"{args.output / f'{args.prefix}_{module.file_suffix}.csv'}"
                )

    if snapshot_defs:
        export_snapshots(
            base=base,
            dpids=tuple(args.dpids or []),
            snapshots=snapshot_defs,
            output_dir=args.output,
            prefix=args.prefix,
            quiet=args.quiet,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
