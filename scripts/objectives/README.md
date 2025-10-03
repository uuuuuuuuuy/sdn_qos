# Objective 脚本说明

该目录提供用于启动控制器、加载实验拓扑以及 Objective 4 常用的采集/绘图封装脚本，便于快速进入 FlowManager 配置流程。更通用的
Python 工具位于 `scripts/tools/` 目录，可满足跨 Objective 的数据导出与可视化需求。QoS 规则仍在 Web UI 中完成，详见
`docs/objectives/README.md`。

## 环境约定

- 默认在仓库根目录执行命令，已按照主仓库 README 配置好虚拟环境与依赖。
- 如果虚拟环境路径不是 `.venv`，可通过环境变量 `SDN_QOS_VENV` 指定。
- Ryu 控制器监听 `6653`（OpenFlow）、`8080`（REST/FlowManager），OVSDB 管理端口为 `6632`。

## 脚本一览

| 脚本 | 目的 | 使用提示 |
| --- | --- | --- |
| `objective1_start_controller.sh` | 启动集成 FlowManager、拓扑模块与 QoS REST 的 Ryu 控制器。 | 在独立终端运行，保持前台输出以便观察日志；执行时会自动调用 `ovs-vsctl set-manager ptcp:6632`（需要 `sudo` 权限）。 |
| `objective2_launch_mininet.sh` | 启动多级树形拓扑（1 核心 + 2 汇聚 + 4 主机），用于更贴近真实网络的 GUI 验证。 | 可通过环境变量 `CTRL_IP` / `CTRL_PORT` 指定远端控制器地址。 |
| `objective3_collect_stats.py` | Objective 3 场景采集脚本，循环提示切换策略后调用 `../tools/export_metrics.py` 抓取端口/流表/队列/QoS 规则。 | 通过 `--scenario baseline --scenario priority --scenario classification` 自定义实验轮次，生成的文件名前缀会自动带上场景名。 |
| `objective4_collect_stats.py` | Objective 4 默认采集封装脚本，会调用 `../tools/export_metrics.py` 并预设端口/队列/Meter/流表统计。 | 常用参数包括 `--duration`、`--interval`、`--modules` 与 `--snapshots`，输出默认存放在 `docs/objectives/data/`。 |
| `objective4_plot.py` | Objective 4 默认图表封装脚本，会调用 `../tools/plot_metrics.py` 生成端口/队列/Meter/流表 Top-N/QoS 汇总图。 | 通过 `--series label=prefix` 汇入多组数据，搭配 `--ports`、`--dpids`、`--topn-flows`、`--charts` 与 `--output` 控制输出。 |
| `objective5_generate_assets.py` | Objective 5 报告素材脚本，基于 `../tools/plot_metrics.py` 生成图像并可选打包 CSV/PNG/模板。 | 结合 `--series label=prefix`、`--archive docs/objectives/bundles/qos.zip` 一次产出论文附件。 |

## 典型流程

1. **启动控制器**：`./scripts/objectives/objective1_start_controller.sh`
2. **加载多级拓扑**：新终端执行 `./scripts/objectives/objective2_launch_mininet.sh`
3. **打开 FlowManager**：浏览器访问 `http://<控制器 IP>:8080/flowmanager/index.html`，根据 `docs/objectives/README.md` 完成 QoS 配置。
4. **实验采集**：
   - Objective 3 使用 `objective3_collect_stats.py` 依序采集 baseline/priority/classification 等场景。
   - Objective 4 利用 `objective4_collect_stats.py`、`objective4_plot.py` 快速生成 QoS 对比数据。
   - Objective 5 阶段可调用 `objective5_generate_assets.py` 统一输出图表并打包归档。
   - 若需跨阶段或自定义采样，可改用 `../tools/export_metrics.py`、`../tools/plot_metrics.py`。

运行结束后按 `Ctrl+C` 停止脚本即可。
