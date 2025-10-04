# 基于 Ryu + FlowManager 的 SDN QoS 管理实验平台

本项目整合 FlowManager 图形界面与 Ryu QoS 扩展，构建了一套可复现的 SDN 网络质量管理实验平台。借助 Mininet 仿真网络、Ryu 控制器与 FlowManager Web UI，可验证按流/按分类的 QoS 保障方案，并生成可直接用于报告或论文的实验数据与图表。

## 功能亮点

- **可视化控制**：集成 FlowManager UI、拓扑可视化与 REST 接口，便于实时查看拓扑、流表、端口统计信息。
- **Web UI 配置流程**：提供以 FlowManager 为核心的目标执行指南，可直接在浏览器内完成 Meter、队列与流表管理。
- **数据采集支持**：提供 `scripts/tools/export_metrics.py` 通用脚本，以及 `scripts/objectives/objective4_collect_stats.py` 的 QoS 场景封装，可按需抓取端口、队列、流表、Meter、Group、QoS 规则及拓扑快照。
- **自动化图表生成**：`scripts/tools/plot_metrics.py` 与 `scripts/objectives/objective4_plot.py` 可批量输出端口/队列/表项曲线与流表 Top-N、QoS 配置等图表，为 Objective 4/5 提供论文级素材。
- **论文支撑材料**：整理实验流程、模板与常见问题，方便撰写技术报告或论文。

## 仓库结构概览

```text
sdn_qos/
├── flowmanager/               # FlowManager 应用源码（已整合至 Ryu）
├── ryu_qos_apps/              # QoS REST 与示例交换机扩展
├── scripts/
│   ├── objectives/            # 启动控制器/拓扑/分目标封装脚本及说明
│   └── tools/                 # 通用数据采集与绘图脚本
├── topology/                  # 数据中心及最小拓扑示例
├── docs/objectives/           # 各阶段目标的执行手册与论文模板
└── README.md                  # 当前文件
```

## 部署准备

1. **准备虚拟环境**（以 `~/.venv` 为例，可按需调整）：
   ```bash
   python3 -m venv ~/.venv
   source ~/.venv/bin/activate
   pip install -U pip
   ```
2. **安装依赖软件**：
   ```bash
   # Mininet
   git clone git://github.com/mininet/mininet
   sudo mininet/util/install.sh -a

   # Ryu 控制器（仓库内应用需要被 Ryu 发现）
   git clone https://github.com/faucetsdn/ryu.git
   cd ryu
   pip install .
   cd -
   ```
   额外依赖：
   ```bash
   pip install eventlet msgpack-python netaddr oslo.config routes six webob \
              tinyrpc requests pandas matplotlib
   sudo apt install libxml2-dev libxslt1-dev libffi-dev iperf3
   ```
以上 `tinyrpc` 为 FlowManager RPC 调用所需依赖，缺失时会导致 FlowManager 在处理 PacketIn 时抛出异常，请务必安装。
3. **拷贝 QoS 应用至 Ryu**：
   ```bash
   cp ryu_qos_apps/*.py <RYU_SOURCE_DIR>/ryu/app/
   ```
4. **（可选）安装 D-ITG 流量发生器**：
   ```bash
   wget http://www.grid.unina.it/software/ITG/codice/D-ITG-2.8.1-r1023-src.zip
   unzip D-ITG-2.8.1-r1023-src.zip
   cd D-ITG-2.8.1-r1023/src
   make
   ```
5. **配置环境变量**：如使用本仓库根目录下的虚拟环境，可在脚本中自动识别；否则请设置 `SDN_QOS_VENV` 指向对应路径。
6. **确认 OVSDB 地址绑定**：
   - `objective1_start_controller.sh` 会在后台轮询 `/stats/switches`，并自动为 `SDN_QOS_OVSDB_DPIDS` 指定的交换机写入 `SDN_QOS_OVSDB_ADDR`（默认值为 `tcp:127.0.0.1:6632`，DPID 列表为 `0000000000000001 0000000000000002 0000000000000003`）。如需禁用此行为，可在运行脚本前设置 `SDN_QOS_AUTO_BIND_OVSDB=0`；如需自定义地址或 DPID，请调整 `SDN_QOS_OVSDB_ADDR`、`SDN_QOS_OVSDB_DPIDS`、`SDN_QOS_API_BASE` 等环境变量。
   - 若自动绑定失败或需要手动重试，可在终端执行：
     ```bash
     for dpid in 0000000000000001 0000000000000002 0000000000000003; do
       curl -X PUT \
         http://127.0.0.1:8080/v1.0/conf/switches/${dpid}/ovsdb_addr \
         -d '"tcp:127.0.0.1:6632"'
     done
     ```
     或在 FlowManager `Messages` 页面的 `Config` 标签选择对应 `Switch ID`，`Rest URL=/v1.0/conf/switches/<dpid>/ovsdb_addr`，`Method=PUT`，`Data` 填写 `"tcp:127.0.0.1:6632"` 并依次提交。
   - 可通过同一页面切换为 `Method=GET`，或运行 `curl -X GET http://127.0.0.1:8080/v1.0/conf/switches/<dpid>/ovsdb_addr` 验证返回值是否正确。若仍返回 `result: failure, details: ovs_bridge is not exists`，请确认交换机已与控制器建立连接或延长自动绑定超时时间（`SDN_QOS_OVSDB_TIMEOUT`）。

完成以上步骤后，请按照下列流程运行项目：

## 运行流程

1. **启动 Ryu + FlowManager**：
   ```bash
   ./scripts/objectives/objective1_start_controller.sh
   ```
   该脚本会激活虚拟环境、自动清理并开放 `ptcp:6632` 管理端口，并在后台尝试为默认 DPID 写入 `ovsdb_addr`（可通过 `SDN_QOS_AUTO_BIND_OVSDB` 等环境变量控制）；必要时会提示输入 `sudo` 密码。
2. **启动树形 Mininet 拓扑**：
   ```bash
   ./scripts/objectives/objective2_launch_mininet.sh
   ```
   拓扑包含 3 台 OVS 与 3 台主机，满足 Objective 1-4 的验证与统计需求。
3. **在 FlowManager 中完成配置与采集**：
   - 浏览器访问 `http://<控制器 IP>:8080/flowmanager/index.html`。
   - 参考 `docs/objectives/README.md`，依序填写 Dashboard/Meter/Flow 表单，并执行 QoS 配置切换、统计导出与 CSV/图表生成。
   - 自动化辅助脚本示例：
     ```bash
     # Objective 3：按场景采集端口/流表/队列/QoS 规则
     python scripts/objectives/objective3_collect_stats.py \
       --controller http://127.0.0.1:8080 \
       --dpid 1 --dpid 2 --dpid 3 \
       --scenario baseline --scenario priority --scenario classification \
       --duration 120 --interval 5 --prefix qos_stage

     # Objective 4：采集端口/队列/Meter/表项并生成快照
     python scripts/objectives/objective4_collect_stats.py \
       --controller http://127.0.0.1:8080 \
       --dpid 1 --dpid 2 --dpid 3 \
       --modules port flow queue meter table qos-queue qos-rule \
       --snapshots topology-switches topology-links topology-hosts port-desc \
       --duration 180 --interval 5 --prefix priority_run

     # Objective 4：多场景图像输出
     python scripts/objectives/objective4_plot.py \
       --series baseline=docs/objectives/data/baseline_run \
       --series priority=docs/objectives/data/priority_run \
       --output docs/objectives/figures/priority_vs_baseline \
       --ports 2 3 --dpids 1 2 3 --topn-flows 8

     # Objective 5：统一生成图表并打包归档
     python scripts/objectives/objective5_generate_assets.py \
       --series baseline=docs/objectives/data/baseline_run \
       --series priority=docs/objectives/data/priority_run \
       --series classification=docs/objectives/data/classification_run \
       --output-dir docs/objectives/figures/qos_report \
       --archive docs/objectives/bundles/qos_report.zip
     ```

### 数据采集与图表自动化示例

- **Objective 1（环境验证）**：
  ```bash
  python scripts/tools/export_metrics.py \
    --controller http://127.0.0.1:8080 \
    --no-modules --snapshots topology-switches topology-links topology-hosts \
    --prefix obj1_topology
  ```
  导出拓扑/主机列表快照，便于报告中展示初始环境。

- **Objective 2（连通性基线）**：
  ```bash
  python scripts/tools/export_metrics.py \
    --controller http://127.0.0.1:8080 \
    --dpid 1 --dpid 2 --dpid 3 \
    --modules port --samples 3 --interval 2 \
    --prefix obj2_baseline
  ```
  快速抓取 3 轮端口统计，用于对比后续 QoS 实验。

- **Objective 3（QoS 策略准备）**：
  ```bash
  python scripts/objectives/objective3_collect_stats.py \
    --controller http://127.0.0.1:8080 \
    --dpid 1 --dpid 2 --dpid 3 \
    --scenario baseline --scenario priority --scenario classification \
    --duration 120 --interval 5 --prefix obj3
  ```
  自动按场景生成 `obj3_baseline_ports.csv`、`obj3_priority_flows.csv` 等文件，便于对比策略切换前后的统计。

- **Objective 4（策略对比）**：
  结合上文的采集与绘图命令，在 `docs/objectives/data/` 与 `docs/objectives/figures/` 下生成端口吞吐、队列速率、Meter/Group 变化、流表 Top-N、QoS 规则表等多类型图像，为论文写作提供完整素材。

- **Objective 5（结果归档）**：
  ```bash
  python scripts/objectives/objective5_generate_assets.py \
    --series baseline=docs/objectives/data/baseline_run \
    --series priority=docs/objectives/data/priority_run \
    --series classification=docs/objectives/data/classification_run \
    --output-dir docs/objectives/figures/qos_report \
    --archive docs/objectives/bundles/qos_report.zip
  ```
  输出 `qos_report/` 下的图表，并生成可直接提交的压缩包与报告模板副本。

生成的 CSV/图像可按实验轮次整理至子目录（例如 `docs/objectives/data/priority_2023-12-01/` 与 `docs/objectives/figures/priority_2023-12-01/`），便于 Objective 5 汇总分析。

依照以上步骤即可直接跑通项目并得到完整的实验数据与对比图表。

## 目标执行指南

为便于项目管理，仓库提供了中文执行手册：

- `docs/objectives/README.md`：针对 Objective 1-5 的 FlowManager 操作步骤、页面字段取值与常见问题（含 Dashboard/Meter/Flow Form 字段填写示例）。
- `docs/objectives/OBJECTIVE5_REPORT_TEMPLATE.md`：论文写作提纲，涵盖架构说明、实验设计、结果分析与总结。

祝顺利完成 Objective 1-5 并写出高质量论文！
