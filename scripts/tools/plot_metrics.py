#!/usr/bin/env python3
"""基于 CSV 统计自动绘制多维度图表。

该脚本与 ``scripts/tools/export_metrics.py`` 或
``scripts/objectives/objective4_collect_stats.py`` 搭配使用，可同时比较多组
实验（例如 baseline / priority / classification），生成论文所需的图表素材：

* 端口：吞吐量、包速率、丢包 / 错误率以及总吞吐对比。
* 队列：各 QoS 队列的吞吐 / 包速率。
* Meter / Group / Table：速率或即时计数变化。
* 流表：按 DPID 输出 Top-N 流量条目条形图。
* QoS 配置：以柱状图展示队列速率、以表格展示规则映射。

示例：
    python scripts/tools/plot_metrics.py \
        --run baseline=docs/objectives/data/baseline_run \
        --run priority=docs/objectives/data/priority_run \
        --run classification=docs/objectives/data/class_run \
        --output-dir docs/objectives/figures \
        --ports 2 3 --dpids 1 2 3 --topn-flows 8

如需 Objective 4 默认图表组合，可运行
``scripts/objectives/objective4_plot.py``。
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import pandas as pd


@dataclass(frozen=True)
class RateMetric:
    source_column: str
    unit: str
    scale: float
    label: str


@dataclass(frozen=True)
class AbsoluteMetric:
    source_column: str
    unit: str
    label: str


PORT_RATE_METRICS: Mapping[str, RateMetric] = {
    "tx_mbps": RateMetric("tx_bytes", "Mbps", 8 / 1_000_000, "端口发送吞吐"),
    "rx_mbps": RateMetric("rx_bytes", "Mbps", 8 / 1_000_000, "端口接收吞吐"),
    "tx_pps": RateMetric("tx_packets", "pps", 1.0, "端口发送包速"),
    "rx_pps": RateMetric("rx_packets", "pps", 1.0, "端口接收包速"),
    "tx_drop_ps": RateMetric("tx_dropped", "drops/s", 1.0, "端口发送丢包率"),
    "rx_drop_ps": RateMetric("rx_dropped", "drops/s", 1.0, "端口接收丢包率"),
    "tx_err_ps": RateMetric("tx_errors", "errors/s", 1.0, "端口发送错误率"),
    "rx_err_ps": RateMetric("rx_errors", "errors/s", 1.0, "端口接收错误率"),
}

QUEUE_RATE_METRICS: Mapping[str, RateMetric] = {
    "queue_tx_mbps": RateMetric("tx_bytes", "Mbps", 8 / 1_000_000, "队列发送吞吐"),
    "queue_tx_pps": RateMetric("tx_packets", "pps", 1.0, "队列发送包速"),
    "queue_err_ps": RateMetric("tx_errors", "errors/s", 1.0, "队列错误率"),
}

METER_RATE_METRICS: Mapping[str, RateMetric] = {
    "meter_byte_ps": RateMetric("byte_in_count", "bytes/s", 1.0, "Meter 字节速率"),
    "meter_packet_ps": RateMetric("packet_in_count", "packets/s", 1.0, "Meter 包速率"),
}

GROUP_RATE_METRICS: Mapping[str, RateMetric] = {
    "group_byte_ps": RateMetric("byte_count", "bytes/s", 1.0, "Group 字节速率"),
    "group_packet_ps": RateMetric("packet_count", "packets/s", 1.0, "Group 包速率"),
}

TABLE_RATE_METRICS: Mapping[str, RateMetric] = {
    "lookup_ps": RateMetric("lookup_count", "lookups/s", 1.0, "表项查询速率"),
    "match_ps": RateMetric("matched_count", "matches/s", 1.0, "表项命中速率"),
}

TABLE_ABSOLUTE_METRICS: Mapping[str, AbsoluteMetric] = {
    "active_count": AbsoluteMetric("active_count", "entries", "活跃表项"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="读取导出的 CSV 数据并绘制综合图表。")
    parser.add_argument(
        "--run",
        action="append",
        metavar="LABEL=PREFIX",
        required=True,
        help="实验标识及 CSV 前缀，例如 priority=docs/objectives/data/priority_run",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="图像输出目录，若不存在会自动创建。",
    )
    parser.add_argument(
        "--figure-format",
        default="png",
        help="输出图片格式（默认 png，可用 svg/pdf 等）。",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=144,
        help="输出分辨率 DPI（默认 144）。",
    )
    parser.add_argument(
        "--ports",
        type=int,
        nargs="*",
        help="仅绘制指定端口号（可多值）。不指定则自动遍历所有端口。",
    )
    parser.add_argument(
        "--dpids",
        type=int,
        nargs="*",
        help="仅绘制指定交换机 DPID。",
    )
    parser.add_argument(
        "--topn-flows",
        type=int,
        default=6,
        help="每个 DPID 绘制的流表 Top-N 数量（默认 6）。",
    )
    parser.add_argument(
        "--title-prefix",
        default="",
        help="为所有图表增加统一标题前缀，便于区分批次。",
    )
    parser.add_argument(
        "--no-port",
        action="store_true",
        help="跳过端口类图表。",
    )
    parser.add_argument(
        "--no-queue",
        action="store_true",
        help="跳过队列类图表。",
    )
    parser.add_argument(
        "--no-meter",
        action="store_true",
        help="跳过 Meter 图表。",
    )
    parser.add_argument(
        "--no-group",
        action="store_true",
        help="跳过 Group 图表。",
    )
    parser.add_argument(
        "--no-table",
        action="store_true",
        help="跳过 Table 图表。",
    )
    parser.add_argument(
        "--no-flow",
        action="store_true",
        help="跳过流表 Top-N 图表。",
    )
    parser.add_argument(
        "--no-qos",
        action="store_true",
        help="跳过 QoS 队列/规则图表。",
    )
    return parser.parse_args()


def parse_runs(run_args: Sequence[str]) -> Mapping[str, Path]:
    runs: MutableMapping[str, Path] = {}
    for item in run_args:
        if "=" not in item:
            raise ValueError(f"--run 参数格式应为 label=prefix：{item}")
        label, prefix = item.split("=", 1)
        path = Path(prefix)
        runs[label] = path
    return runs


def load_csv(path: Path, *, parse_dates: Optional[Sequence[str]] = None) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    return pd.read_csv(path, parse_dates=list(parse_dates) if parse_dates else None)


def resolve_csv_path(prefix: Path, suffix: str) -> Path:
    raw = str(prefix)
    if raw.endswith(f"_{suffix}.csv"):
        return Path(raw)
    if raw.endswith(".csv"):
        raw = raw[:-4]
    return Path(f"{raw}_{suffix}.csv")


def ensure_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def rate_by_groups(
    df: pd.DataFrame,
    group_cols: Sequence[str],
    metric: RateMetric,
    metric_name: str,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(group_cols) + ["timestamp", metric_name])
    work = df.copy()
    work = ensure_numeric(work, list(group_cols) + [metric.source_column])
    work.dropna(subset=list(group_cols) + [metric.source_column, "timestamp"], inplace=True)
    if work.empty:
        return pd.DataFrame(columns=list(group_cols) + ["timestamp", metric_name])
    work["timestamp"] = pd.to_datetime(work["timestamp"])
    sort_cols = list(group_cols) + ["timestamp"]
    work.sort_values(sort_cols, inplace=True)
    grouped = work.groupby(list(group_cols), sort=False)
    work["delta"] = grouped["timestamp"].diff().dt.total_seconds()
    work["diff"] = grouped[metric.source_column].diff()
    valid = work[(work["delta"] > 0) & (work["diff"] >= 0)]
    if valid.empty:
        return pd.DataFrame(columns=list(group_cols) + ["timestamp", metric_name])
    valid[metric_name] = valid["diff"] * metric.scale / valid["delta"]
    return valid[list(group_cols) + ["timestamp", metric_name]]


def absolute_by_groups(
    df: pd.DataFrame,
    group_cols: Sequence[str],
    metric: AbsoluteMetric,
    metric_name: str,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=list(group_cols) + ["timestamp", metric_name])
    work = df.copy()
    work = ensure_numeric(work, list(group_cols))
    work.dropna(subset=list(group_cols) + [metric.source_column, "timestamp"], inplace=True)
    if work.empty:
        return pd.DataFrame(columns=list(group_cols) + ["timestamp", metric_name])
    work["timestamp"] = pd.to_datetime(work["timestamp"])
    sort_cols = list(group_cols) + ["timestamp"]
    work.sort_values(sort_cols, inplace=True)
    work = work[list(group_cols) + ["timestamp", metric.source_column]]
    work.rename(columns={metric.source_column: metric_name}, inplace=True)
    return work


def filter_combinations(
    combinations: Iterable[Tuple[int, ...]],
    dpids: Optional[Sequence[int]],
    ports: Optional[Sequence[int]],
) -> List[Tuple[int, ...]]:
    filtered: List[Tuple[int, ...]] = []
    for combo in combinations:
        if dpids and combo[0] not in dpids:
            continue
        if ports and len(combo) > 1 and combo[1] not in ports:
            continue
        filtered.append(combo)
    return sorted(filtered)


def create_category_dir(base: Path, name: str) -> Path:
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def render_timeseries(
    out_dir: Path,
    figure_format: str,
    dpi: int,
    title: str,
    ylabel: str,
    metric_name: str,
    combos: Sequence[Tuple[int, ...]],
    data: Mapping[str, pd.DataFrame],
    index_cols: Sequence[str],
    label_suffix: str,
    title_prefix: str,
    filename_template: str,
) -> None:
    for combo in combos:
        has_series = False
        plt.figure(figsize=(10, 5))
        for label, df in data.items():
            subset = df.copy()
            for col, value in zip(index_cols, combo):
                subset = subset[subset[col] == value]
            if subset.empty:
                continue
            has_series = True
            plt.plot(subset["timestamp"], subset[metric_name], marker="o", label=label)
        if not has_series:
            plt.close()
            continue
        combo_text = " / ".join(str(item) for item in combo)
        plt.title(f"{title_prefix}{title} - {label_suffix}{combo_text}")
        plt.xlabel("时间")
        plt.ylabel(ylabel)
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        filename = filename_template.format(*combo)
        output = out_dir / f"{filename}.{figure_format}"
        plt.savefig(output, dpi=dpi)
        plt.close()


def render_aggregate(
    out_dir: Path,
    figure_format: str,
    dpi: int,
    title: str,
    ylabel: str,
    metric_name: str,
    data: Mapping[str, pd.DataFrame],
    title_prefix: str,
) -> None:
    plt.figure(figsize=(10, 5))
    has_series = False
    for label, df in data.items():
        if df.empty:
            continue
        grouped = df.groupby("timestamp")[metric_name].sum().reset_index()
        if grouped.empty:
            continue
        has_series = True
        plt.plot(grouped["timestamp"], grouped[metric_name], marker="o", label=label)
    if not has_series:
        plt.close()
        return
    plt.title(f"{title_prefix}{title}")
    plt.xlabel("时间")
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    output = out_dir / f"aggregate_{metric_name}.{figure_format}"
    plt.savefig(output, dpi=dpi)
    plt.close()


def render_flow_topn(
    out_dir: Path,
    figure_format: str,
    dpi: int,
    flow_frames: Mapping[str, pd.DataFrame],
    dpids: Optional[Sequence[int]],
    topn: int,
    title_prefix: str,
) -> None:
    all_dpids: List[int] = sorted({int(dpid) for df in flow_frames.values() for dpid in df["dpid"].unique()})
    if dpids:
        all_dpids = [d for d in all_dpids if d in dpids]
    for dpid in all_dpids:
        plt.figure(figsize=(10, 6))
        has_data = False
        legend_used: set[str] = set()
        for label, df in flow_frames.items():
            subset = df[df["dpid"] == dpid]
            if subset.empty:
                continue
            has_data = True
            top = subset.nlargest(topn, "byte_mbps")
            plt.barh(
                [f"{label}\n{idx}" for idx in top["flow_id"]],
                top["byte_mbps"],
                label=label if label not in legend_used else None,
                alpha=0.7,
            )
            legend_used.add(label)
        if not has_data:
            plt.close()
            continue
        plt.title(f"{title_prefix}DPID {dpid} 流表 Top-{topn} 吞吐")
        plt.xlabel("Mbps")
        plt.tight_layout()
        if legend_used:
            plt.legend()
        output = out_dir / f"flow_top{topn}_dp{dpid}.{figure_format}"
        plt.savefig(output, dpi=dpi)
        plt.close()


def render_qos_queue(
    out_dir: Path,
    figure_format: str,
    dpi: int,
    qos_frames: Mapping[str, pd.DataFrame],
    title_prefix: str,
) -> None:
    for label, df in qos_frames.items():
        if df.empty:
            continue
        latest = df.sort_values("timestamp").drop_duplicates(
            subset=["dpid", "port_name", "queue_id"], keep="last"
        )
        latest = ensure_numeric(latest, ["min_rate", "max_rate", "burst", "priority"])
        latest.fillna(0, inplace=True)
        latest["queue_label"] = (
            "dpid="
            + latest["dpid"].astype(int).astype(str)
            + ",port="
            + latest["port_name"].astype(str)
            + ",queue="
            + latest["queue_id"].astype(str)
        )
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(latest["queue_label"], latest["max_rate"], color="#1f77b4", label="max_rate")
        ax.bar(latest["queue_label"], latest["min_rate"], color="#ff7f0e", label="min_rate")
        ax.set_title(f"{title_prefix}{label} QoS 队列速率配置")
        ax.set_ylabel("kbps")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        ax.legend()
        fig.tight_layout()
        output = out_dir / f"qos_queue_{label}.{figure_format}"
        fig.savefig(output, dpi=dpi)
        plt.close(fig)


def render_qos_rules(
    out_dir: Path,
    figure_format: str,
    dpi: int,
    qos_rules: Mapping[str, pd.DataFrame],
    title_prefix: str,
) -> None:
    for label, df in qos_rules.items():
        if df.empty:
            continue
        latest = df.sort_values("timestamp").drop_duplicates(
            subset=["dpid", "rule_id"], keep="last"
        )
        latest["match"] = latest["match"].astype(str)
        latest["actions"] = latest["actions"].astype(str)
        latest.sort_values(["dpid", "priority", "rule_id"], inplace=True)
        fig, ax = plt.subplots(figsize=(12, 0.5 * max(len(latest), 1) + 2))
        ax.axis("off")
        table_data = [
            [
                row["dpid"],
                row["rule_id"],
                row["priority"],
                row["queue"],
                row["match"],
                row["actions"],
            ]
            for _, row in latest.iterrows()
        ]
        table = ax.table(
            cellText=table_data,
            colLabels=["DPID", "规则ID", "优先级", "队列", "匹配", "动作"],
            loc="center",
            cellLoc="left",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        ax.set_title(f"{title_prefix}{label} QoS 规则汇总", pad=20)
        fig.tight_layout()
        output = out_dir / f"qos_rules_{label}.{figure_format}"
        fig.savefig(output, dpi=dpi)
        plt.close(fig)


def main() -> int:
    args = parse_args()
    runs = parse_runs(args.run)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    port_frames: Dict[str, pd.DataFrame] = {}
    queue_frames: Dict[str, pd.DataFrame] = {}
    meter_frames: Dict[str, pd.DataFrame] = {}
    group_frames: Dict[str, pd.DataFrame] = {}
    table_frames: Dict[str, pd.DataFrame] = {}
    flow_frames: Dict[str, pd.DataFrame] = {}
    qos_queue_frames: Dict[str, pd.DataFrame] = {}
    qos_rule_frames: Dict[str, pd.DataFrame] = {}

    for label, prefix in runs.items():
        port_path = resolve_csv_path(prefix, "ports")
        port_df = load_csv(port_path, parse_dates=["timestamp"]) or pd.DataFrame()
        port_frames[label] = ensure_numeric(port_df, ["dpid", "port_no"])

        queue_path = resolve_csv_path(prefix, "queues")
        queue_df = load_csv(queue_path, parse_dates=["timestamp"]) or pd.DataFrame()
        queue_frames[label] = ensure_numeric(queue_df, ["dpid", "port_no", "queue_id"])

        meter_path = resolve_csv_path(prefix, "meters")
        meter_frames[label] = ensure_numeric(
            load_csv(meter_path, parse_dates=["timestamp"]) or pd.DataFrame(),
            ["dpid", "meter_id"],
        )

        group_path = resolve_csv_path(prefix, "groups")
        group_frames[label] = ensure_numeric(
            load_csv(group_path, parse_dates=["timestamp"]) or pd.DataFrame(),
            ["dpid", "group_id"],
        )

        table_path = resolve_csv_path(prefix, "tables")
        table_frames[label] = ensure_numeric(
            load_csv(table_path, parse_dates=["timestamp"]) or pd.DataFrame(),
            ["dpid", "table_id"],
        )

        flow_path = resolve_csv_path(prefix, "flows")
        flow_df = load_csv(flow_path, parse_dates=["timestamp"]) or pd.DataFrame()
        if not flow_df.empty:
            flow_df["timestamp"] = pd.to_datetime(flow_df["timestamp"])
            flow_df.sort_values("timestamp", inplace=True)
            grouped = flow_df.groupby(["dpid", "priority", "cookie", "match"], as_index=False).last()
            grouped = ensure_numeric(grouped, ["dpid", "priority", "cookie", "byte_count"])
            grouped.dropna(subset=["dpid", "byte_count"], inplace=True)
            grouped["dpid"] = grouped["dpid"].astype("Int64")
            grouped["priority"] = grouped["priority"].astype("Int64")
            grouped["cookie"] = grouped["cookie"].astype("Int64")
            grouped["byte_mbps"] = grouped["byte_count"].astype(float) * 8 / 1_000_000
            grouped["flow_id"] = (
                "prio="
                + grouped["priority"].astype(str)
                + ",cookie="
                + grouped["cookie"].astype(str)
            )
            flow_frames[label] = grouped
        else:
            flow_frames[label] = pd.DataFrame(columns=["dpid", "byte_mbps", "flow_id"])

        qos_queue_path = resolve_csv_path(prefix, "qos_queues")
        qos_queue_frames[label] = load_csv(qos_queue_path, parse_dates=["timestamp"]) or pd.DataFrame()

        qos_rule_path = resolve_csv_path(prefix, "qos_rules")
        qos_rule_frames[label] = load_csv(qos_rule_path, parse_dates=["timestamp"]) or pd.DataFrame()

    figure_format = args.figure_format.lstrip(".")

    if not args.no_port:
        port_dir = create_category_dir(args.output_dir, "ports")
        port_metric_frames: Dict[str, Dict[str, pd.DataFrame]] = {}
        for label, df in port_frames.items():
            port_metric_frames[label] = {}
            for metric_name, metric in PORT_RATE_METRICS.items():
                port_metric_frames[label][metric_name] = rate_by_groups(
                    df, ["dpid", "port_no"], metric, metric_name
                )
        combos_all = {
            (int(row["dpid"]), int(row["port_no"]))
            for df in port_frames.values()
            for _, row in df.dropna(subset=["dpid", "port_no"]).iterrows()
        }
        combos = filter_combinations(combos_all, args.dpids, args.ports)
        for metric_name, metric in PORT_RATE_METRICS.items():
            data = {label: frames[metric_name] for label, frames in port_metric_frames.items()}
            render_timeseries(
                out_dir=port_dir,
                figure_format=figure_format,
                dpi=args.dpi,
                title=metric.label,
                ylabel=metric.unit,
                metric_name=metric_name,
                combos=combos,
                data=data,
                index_cols=["dpid", "port_no"],
                label_suffix="DPID/Port ",
                title_prefix=args.title_prefix,
                filename_template="port_{0}_{1}_" + metric_name,
            )
            render_aggregate(
                out_dir=port_dir,
                figure_format=figure_format,
                dpi=args.dpi,
                title=f"{metric.label} 汇总",
                ylabel=metric.unit,
                metric_name=metric_name,
                data=data,
                title_prefix=args.title_prefix,
            )

    if not args.no_queue:
        queue_dir = create_category_dir(args.output_dir, "queues")
        queue_metric_frames: Dict[str, Dict[str, pd.DataFrame]] = {}
        combos_all = set()
        for label, df in queue_frames.items():
            queue_metric_frames[label] = {}
            if not df.empty:
                df = ensure_numeric(df, ["dpid", "port_no", "queue_id"])
            for metric_name, metric in QUEUE_RATE_METRICS.items():
                queue_metric_frames[label][metric_name] = rate_by_groups(
                    df, ["dpid", "port_no", "queue_id"], metric, metric_name
                )
            combos_all.update(
                {
                    (
                        int(row["dpid"]),
                        int(row["port_no"]),
                        int(row["queue_id"]),
                    )
                    for _, row in df.dropna(subset=["dpid", "port_no", "queue_id"]).iterrows()
                }
            )
        combos = filter_combinations(combos_all, args.dpids, args.ports)
        for metric_name, metric in QUEUE_RATE_METRICS.items():
            data = {label: frames[metric_name] for label, frames in queue_metric_frames.items()}
            render_timeseries(
                out_dir=queue_dir,
                figure_format=figure_format,
                dpi=args.dpi,
                title=metric.label,
                ylabel=metric.unit,
                metric_name=metric_name,
                combos=combos,
                data=data,
                index_cols=["dpid", "port_no", "queue_id"],
                label_suffix="DPID/Port/Queue ",
                title_prefix=args.title_prefix,
                filename_template="queue_{0}_{1}_{2}_" + metric_name,
            )

    if not args.no_meter:
        meter_dir = create_category_dir(args.output_dir, "meters")
        meter_metric_frames: Dict[str, Dict[str, pd.DataFrame]] = {}
        combos_all = set()
        for label, df in meter_frames.items():
            meter_metric_frames[label] = {}
            for metric_name, metric in METER_RATE_METRICS.items():
                meter_metric_frames[label][metric_name] = rate_by_groups(
                    df, ["dpid", "meter_id"], metric, metric_name
                )
            combos_all.update(
                {
                    (int(row["dpid"]), int(row["meter_id"]))
                    for _, row in df.dropna(subset=["dpid", "meter_id"]).iterrows()
                }
            )
        combos = filter_combinations(combos_all, args.dpids, None)
        for metric_name, metric in METER_RATE_METRICS.items():
            data = {label: frames[metric_name] for label, frames in meter_metric_frames.items()}
            render_timeseries(
                out_dir=meter_dir,
                figure_format=figure_format,
                dpi=args.dpi,
                title=metric.label,
                ylabel=metric.unit,
                metric_name=metric_name,
                combos=combos,
                data=data,
                index_cols=["dpid", "meter_id"],
                label_suffix="DPID/Meter ",
                title_prefix=args.title_prefix,
                filename_template="meter_{0}_{1}_" + metric_name,
            )

    if not args.no_group:
        group_dir = create_category_dir(args.output_dir, "groups")
        group_metric_frames: Dict[str, Dict[str, pd.DataFrame]] = {}
        combos_all = set()
        for label, df in group_frames.items():
            group_metric_frames[label] = {}
            for metric_name, metric in GROUP_RATE_METRICS.items():
                group_metric_frames[label][metric_name] = rate_by_groups(
                    df, ["dpid", "group_id"], metric, metric_name
                )
            combos_all.update(
                {
                    (int(row["dpid"]), int(row["group_id"]))
                    for _, row in df.dropna(subset=["dpid", "group_id"]).iterrows()
                }
            )
        combos = filter_combinations(combos_all, args.dpids, None)
        for metric_name, metric in GROUP_RATE_METRICS.items():
            data = {label: frames[metric_name] for label, frames in group_metric_frames.items()}
            render_timeseries(
                out_dir=group_dir,
                figure_format=figure_format,
                dpi=args.dpi,
                title=metric.label,
                ylabel=metric.unit,
                metric_name=metric_name,
                combos=combos,
                data=data,
                index_cols=["dpid", "group_id"],
                label_suffix="DPID/Group ",
                title_prefix=args.title_prefix,
                filename_template="group_{0}_{1}_" + metric_name,
            )

    if not args.no_table:
        table_dir = create_category_dir(args.output_dir, "tables")
        table_metric_frames: Dict[str, Dict[str, pd.DataFrame]] = {}
        combos_all = set()
        for label, df in table_frames.items():
            table_metric_frames[label] = {}
            for metric_name, metric in TABLE_RATE_METRICS.items():
                table_metric_frames[label][metric_name] = rate_by_groups(
                    df, ["dpid", "table_id"], metric, metric_name
                )
            for metric_name, metric in TABLE_ABSOLUTE_METRICS.items():
                table_metric_frames[label][metric_name] = absolute_by_groups(
                    df, ["dpid", "table_id"], metric, metric_name
                )
            combos_all.update(
                {
                    (int(row["dpid"]), int(row["table_id"]))
                    for _, row in df.dropna(subset=["dpid", "table_id"]).iterrows()
                }
            )
        combos = filter_combinations(combos_all, args.dpids, None)
        for metric_name, metric in TABLE_RATE_METRICS.items():
            data = {label: frames[metric_name] for label, frames in table_metric_frames.items()}
            render_timeseries(
                out_dir=table_dir,
                figure_format=figure_format,
                dpi=args.dpi,
                title=metric.label,
                ylabel=metric.unit,
                metric_name=metric_name,
                combos=combos,
                data=data,
                index_cols=["dpid", "table_id"],
                label_suffix="DPID/Table ",
                title_prefix=args.title_prefix,
                filename_template="table_{0}_{1}_" + metric_name,
            )
        for metric_name, metric in TABLE_ABSOLUTE_METRICS.items():
            data = {label: frames[metric_name] for label, frames in table_metric_frames.items()}
            render_timeseries(
                out_dir=table_dir,
                figure_format=figure_format,
                dpi=args.dpi,
                title=metric.label,
                ylabel=metric.unit,
                metric_name=metric_name,
                combos=combos,
                data=data,
                index_cols=["dpid", "table_id"],
                label_suffix="DPID/Table ",
                title_prefix=args.title_prefix,
                filename_template="table_{0}_{1}_" + metric_name,
            )

    if not args.no_flow:
        flow_dir = create_category_dir(args.output_dir, "flows")
        render_flow_topn(
            out_dir=flow_dir,
            figure_format=figure_format,
            dpi=args.dpi,
            flow_frames=flow_frames,
            dpids=args.dpids,
            topn=args.topn_flows,
            title_prefix=args.title_prefix,
        )

    if not args.no_qos:
        qos_dir = create_category_dir(args.output_dir, "qos")
        render_qos_queue(
            out_dir=qos_dir,
            figure_format=figure_format,
            dpi=args.dpi,
            qos_frames=qos_queue_frames,
            title_prefix=args.title_prefix,
        )
        render_qos_rules(
            out_dir=qos_dir,
            figure_format=figure_format,
            dpi=args.dpi,
            qos_rules=qos_rule_frames,
            title_prefix=args.title_prefix,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
