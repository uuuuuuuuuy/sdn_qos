# SDN QoS 项目目标执行手册

本手册聚焦于借助 FlowManager Web UI 完成项目五个阶段目标。请确保已按照仓库 README 完成依赖安装，并使用脚本启动 Ryu 控制器与 Mininet 拓扑。

## FlowManager 快速索引

下表列出了在完成各 Objective 时需要访问的页面、必须填写的字段及推荐示例值。示例以仓库提供的树形拓扑（核心交换机 `s1`、汇聚交换机 `s2/s3`、主机 `h1`-`h4`）为基准，可按实际拓扑调整。

| 页面（文件） | 用途 | 关键字段与示例值 |
| --- | --- | --- |
| **Dashboard** (`index.html`) | 查看全局统计、切换交换机 | `Switch ID(s)`：优先选择核心交换机 `0000000000000001`（`s1`），也可在对比阶段切换 `s2/s3`；`Refresh Interval`：保持默认 `5` 秒；端口卡片右上角 `↔` 可放大以截图 |
| **Topology** (`topology.html`) | 验证拓扑加载情况 | 画布左下角 `Lock Layout`：关闭以手动拖拽；拖拽确保 `s1` 位于中心，`s2`、`s3` 分别连接 `h1/h2`、`h3/h4`，右侧面板确认各主机 `ipv4=10.0.0.x` |
| **Flow Tables** (`flows.html`) | 检查当前流表 | 顶部 `Switches` 依次检查 `s1`、`s2`、`s3`；`Table Id` 筛选 `0`；确认 `simple_switch_13` 学习到的 `in_port` ↔ `OUTPUT` 条目 |
| **Flow Form** (`flowform.html`) | 新增/修改流表项 | `Flow Operation=Add`；`Table Id=0`；`Priority`：关键业务示例填 `200`；`Match Fields`：`in_port=1`、`eth_type=0x0800`、`ip_proto=17`、`udp_dst=5002`（对应 `h1→h4` UDP 流）；`Apply Actions`：`OUTPUT→2`（`s1` 上连接 `s3` 的端口，可在 `Topology` 面板确认编号），必要时新增 `SET_QUEUE→{"queue_id":1}`；拥塞场景填写 `Goto Meter=1` |
| **Meter Control** (`meterform.html`) | 创建速率限制 | `Meter ID=1`；`Meter Bands[0]`：`Band Type=DROP`，勾选 `Rate in Kbps` 后 `Rate=20000`、`Burst Size=5000`；提交后在页面下方确认返回 `status: success` |
| **Configuration** (`config.html`) | 备份/恢复配置 | `Save`：`File Name=baseline`/`priority`/`classification`；`Restore`：`Choose File` 选中 `.bk` 后点击 `Restore` |
| **Messages** (`messages.html`) | 采集日志与统计 | `Stats` 标签页 `Switch=s1`，`Stat Type=Port` 或 `Flow`；`Messages` 标签用于导出 `flow_removed` 记录 |

建议在浏览器中同时打开 FlowManager 多个标签页，以便在配置与监控之间快速切换。

---

## Objective 1：搭建测试环境

1. **启动控制器**：在终端运行 `./scripts/objectives/objective1_start_controller.sh`，脚本会启用 FlowManager、拓扑可视化与 QoS REST 应用，并自动开放 OVSDB 管理端口 `ptcp:6632`；首次执行可能提示输入 `sudo` 密码。
2. **确认服务可用**：等待脚本输出 `HTTP serving on http://0.0.0.0:8080`，随后在浏览器访问 `http://<控制器 IP>:8080/flowmanager/index.html`。
3. **验证基础状态采集**：
   - Dashboard 页面的 `Switch ID(s)` 下拉菜单在交换机未上线时为空，属正常现象；上线后请选择 `0000000000000001`。
   - 保持 `Refresh Interval=5` 秒，检查 `Ports stats` 与 `Flow Summary` 卡片时间戳是否更新。尚无交换机连接时会显示 “No data to display...”，即可判定 Objective 1 完成。
4. **常见排查**：Dashboard 右上角 `Messages` 链接可查看日志；若页面无法访问，请检查 8080 端口、防火墙及浏览器缓存（可按 `Ctrl+F5`）。

> 快照建议：
> ```bash
> python scripts/tools/export_metrics.py \
>   --controller http://127.0.0.1:8080 \
>   --no-modules --snapshots topology-switches topology-links topology-hosts \
>   --prefix obj1_topology
> ```
> 将生成 `obj1_topology_topology_switches.csv` / `_links.csv` / `_hosts.csv`，可在 Objective 5 报告中展示环境初始化结果。

---

## Objective 2：树形拓扑与 GUI 验证

1. **启动拓扑**：保持控制器运行，在新终端执行 `./scripts/objectives/objective2_launch_mininet.sh`，加载 `tree,depth=2,fanout=2` 拓扑（核心 `s1`、汇聚 `s2/s3`、主机 `h1-h4`）。
2. **连通性测试**：在 Mininet CLI 运行 `pingall`，输出 `*** Results: 0% dropped` 即可确认跨层互通，可继续保留 CLI 以便后续 `iperf3` 测试。
3. **拓扑确认**：刷新 `topology.html`，应出现 `s1` 位于中心、`s2`/`s3` 分别连接 `h1/h2` 与 `h3/h4` 的结构。点击节点验证 `s1` 具备两条南向链路，主机属性面板显示 `ipv4=10.0.0.x`。
4. **流表与统计检查**：
   - 打开 `flows.html`，依次选择 `s1`、`s2`、`s3`，确认 `simple_switch_13` 为每个端口学习到 `in_port` ↔ `OUTPUT` 条目，尤其是 `s1` 上 `in_port=1` ↔ `OUTPUT:2`（指向 `s3`）。
   - 在 Dashboard `Ports stats` 中点击 `↔` 放大卡片，关注 `s1-eth1/eth2` 与 `s2-eth1` 等端口 `rx-bytes`/`tx-bytes` 随 `pingall` 增长。如需记录基线值，可点击 `Pause` 停止刷新。
5. **REST 接口验证（可选）**：打开浏览器开发者工具 Network 面板，确认周期性请求 `GET /flowmanager/data?portstat=0000000000000001` 返回 JSON 数据。

> 基线采集示例：
> ```bash
> python scripts/tools/export_metrics.py \
>   --controller http://127.0.0.1:8080 \
>   --dpid 1 --dpid 2 --dpid 3 \
>   --modules port --samples 3 --interval 2 \
>   --prefix obj2_baseline
> ```
> 生成的 `obj2_baseline_ports.csv` 可作为后续 QoS 策略的基线数据。

---

## Objective 3：准备 QoS 配置并验证关键业务保障

目标是基于 FlowManager 创建“普通业务/拥塞业务”两套可切换配置，确保跨层关键流量（示例为 `h1→h4` 的 UDP 5002）优先。

### 前置步骤：确认 OVSDB 地址绑定

- `objective1_start_controller.sh` 启动后会在后台自动检测 `/stats/switches`，并为 `SDN_QOS_OVSDB_DPIDS` 环境变量列出的交换机（默认 `0000000000000001 0000000000000002 0000000000000003`）写入 `SDN_QOS_OVSDB_ADDR`（默认 `tcp:127.0.0.1:6632`）。终端将输出 “自动 OVSDB 绑定助手已启动” 等提示，可通过设置 `SDN_QOS_AUTO_BIND_OVSDB=0` 禁用，或通过 `SDN_QOS_OVSDB_TIMEOUT`、`SDN_QOS_OVSDB_POLL_INTERVAL` 调整等待时长。若在日志中看到 `ovs-vsctl: no managers defined` 等信息，可忽略，脚本会继续设置新的管理通道。
- 如需手动重试或在自定义拓扑中补充更多交换机，可使用下列方式：
  - **终端命令**：
    ```bash
    for dpid in 0000000000000001 0000000000000002 0000000000000003; do
      curl -X PUT \
        http://127.0.0.1:8080/v1.0/conf/switches/${dpid}/ovsdb_addr \
        -d '"tcp:127.0.0.1:6632"'
    done
    ```
  - **FlowManager Messages 页面**：切换到 `Config` 标签，依次选择 `Switch ID`，填写 `Rest URL=/v1.0/conf/switches/<dpid>/ovsdb_addr`、`Method=PUT`、`Data="tcp:127.0.0.1:6632"` 后点击 `Send`。
- **验证结果**：将 `Method` 切换为 `GET` 继续发送，或在终端运行 `curl -X GET http://127.0.0.1:8080/v1.0/conf/switches/<dpid>/ovsdb_addr`。若响应仍为空或提示 `ovs_bridge is not exists`，请确认交换机已出现在 Dashboard `Switch ID(s)` 下拉菜单中，或延长自动绑定等待时长后再次执行。

确认 OVSDB 地址生效后，再继续下表中的配置流程。

| 步骤 | 页面 | 字段 | 示例值 / 说明 |
| --- | --- | --- | --- |
| 1 | `config.html` | `Config Scope` | 选择 `--ALL--`，备份所有对象 |
|   |  | `File Name` | 输入 `baseline`，点击 `Save` 下载 `baseline.bk` |
| 2 | `meterform.html` | `Switch ID` | 选择 `0000000000000001` |
|   |  | `Meter Operation` | `Add` |
|   |  | `Meter ID` | `1` |
|   |  | `Flags` | 勾选 `Rate in Kbps`（即 `KBPS` 标志） |
|   |  | `Meter Bands[0]` | `Band Type=DROP`，`Rate=20000`，`Burst Size=5000`；若网络带宽不同，可按需调整 |
|   |  | 提交后验证 | 页面底部 `Result` 区域需显示 `status: success` |
| 3 | `flowform.html` | `Switch ID` | 选择 `0000000000000001`（核心交换机 `s1`） |
|   |  | `Flow Operation` | `Add` |
|   |  | `Table Id` | `0` |
|   |  | `Priority` | `200` |
|   |  | `Cookie` | `0x1`（用于区分关键业务） |
|   |  | `Match Fields` | `in_port=1`（来自 `s2`）、`eth_type=0x0800`、`ip_proto=17`、`udp_dst=5002` |
|   |  | `Apply Actions[0]` | `OUTPUT`，`Value=2`（发往 `s3`/`h4` 的端口，具体编号以 `Topology` 页面为准） |
|   |  | `Apply Actions[1]`（可选） | `SET_QUEUE`，`Value={"queue_id":1}`；需提前使用 `ovs-vsctl` 在 `s1-eth2` 上创建队列 |
|   |  | 提交后验证 | `flows.html` 中应出现 `priority=200`、`cookie=0x1` 的条目，`byte_count` 随 UDP 业务增长 |
| 4 | `flowform.html` | 普通业务流 | `Priority=100`；`Match Fields`：保留 `in_port=1`、`eth_type=0x0800`；若需限制 TCP，可补充 `ip_proto=6` |
|   |  | `Goto Meter` | 填写 `1`，使普通业务流量进入上一步创建的 Meter |
|   |  | `Apply Actions[0]` | `OUTPUT`，`Value=2`（保持与关键业务相同的出口） |
|   |  | 提交后验证 | `flows.html` 中出现 `priority=100` 的条目，普通业务 `byte_count` 将受 Meter 速率限制 |
| 5 | `config.html` | 备份拥塞策略 | `File Name=priority`，点击 `Save` 下载 `priority.bk` |

完成后，可在 Mininet 中执行：
```bash
# 关键业务
iperf3 -s -p 5002 &  # 在 h4 上启动
iperf3 -c 10.0.0.4 -u -b 30M -t 30 -p 5002  # 在 h1 上发起

# 普通业务
iperf3 -s -p 5003 &  # 在 h4 上启动
iperf3 -c 10.0.0.4 -u -b 50M -t 30 -p 5003
```
结合 Dashboard `Ports stats` 与 `messages.html -> Stats`，验证关键业务吞吐保持、普通业务受限。

> 自动化采集建议：
> ```bash
> python scripts/objectives/objective3_collect_stats.py \
>   --controller http://127.0.0.1:8080 \
>   --dpid 1 --dpid 2 --dpid 3 \
>   --scenario baseline --scenario priority --scenario classification \
>   --duration 120 --interval 5 \
>   --prefix qos_stage
> ```
> 针对每套策略切换时运行一次，保留端口吞吐、流表条目、队列配置与端口描述等完整采样。

---

## Objective 4：对比三种策略并导出结果

1. **准备配置文件**：
   - `baseline.bk`：Objective 3 第 1 步生成。
   - `priority.bk`：Objective 3 第 5 步生成。
   - `classification.bk`：在 `flowform.html` 新增以下规则后备份：
     - 规则 A：`Priority=180`、`Match`：`ip_dscp=8`、`in_port=1`；`Apply Actions[0]=OUTPUT→2`。
     - 规则 B：`Priority=90`、`Match`：`tcp_dst=5001`；`Goto Meter=1`；`Apply Actions[0]=OUTPUT→2`。
     - 确认 `flows.html` 中显示对应条目，再到 `config.html` 输入 `classification` 保存。
   - 建议将 `.bk` 文件与实验脚本统一放入 `docs/objectives/configs/`（手动创建目录）。
2. **执行三轮实验**：每轮实验遵循以下流程：
   1. 在 `config.html` 选择 `Switch ID=0000000000000001`，点击 `Choose File` 导入目标 `.bk` 并执行 `Restore`，等待 `status: success`。
   2. 返回 Dashboard，`Switch ID(s)` 选择 `0000000000000001`，点击卡片右上角 `⟳` 强制刷新初始统计。
   3. 在 Mininet CLI 中运行与 Objective 3 相同的流量脚本，每轮持续不少于 30 秒；测试完毕后使用 `jobs` + `kill` 关闭后台 `iperf3` 进程。
3. **采集统计数据**：
   - 每轮实验结束前运行：
     ```bash
     python scripts/objectives/objective4_collect_stats.py \
       --controller http://127.0.0.1:8080 \
       --dpid 1 --dpid 2 --dpid 3 \
       --modules port flow queue meter table qos-queue qos-rule \
       --snapshots topology-switches topology-links topology-hosts port-desc \
       --duration 180 --interval 5 \
       --prefix priority_run
     ```
     会在 `docs/objectives/data/` 下生成 `priority_run_ports.csv`、`_flows.csv`、`_queues.csv`、`_meters.csv`、`_tables.csv` 等文件，以及拓扑/端口描述快照。为 baseline、classification 轮次更换 `--prefix` 后重复执行即可。
   - 如需补充截图，可继续在 Dashboard `Ports stats` 中点击 `↔` 放大 → `Pause` 固定值后复制。
   - `messages.html -> Stats`：`Switch=s1`、`Stat Type=Port` 或 `Flow`，点击 `Start` 收集曲线，结束时点击 `Stop` 并通过浏览器“另存为”保存 PNG/SVG。
4. **绘制图表与整理归档**：
   - 使用绘图脚本一次生成端口、队列、Meter、表项以及流表 Top-N 图像：
     ```bash
     python scripts/objectives/objective4_plot.py \
       --series baseline=docs/objectives/data/baseline_run \
       --series priority=docs/objectives/data/priority_run \
       --series classification=docs/objectives/data/classification_run \
       --output docs/objectives/figures/qos_comparison \
       --ports 2 3 --dpids 1 2 3 --topn-flows 8
     ```
     输出目录会按照类别拆分（`ports/`、`queues/`、`meters/`、`flows/`、`qos/` 等），自动生成时间序列对比图与 QoS 配置汇总表。
   - 为每轮实验创建独立目录（示例：`docs/objectives/data/priority_2023-12-01/` 与 `docs/objectives/figures/priority_2023-12-01/`），整理 `.bk`、CSV、生成的 PNG/SVG、`iperf3.log` 与测试脚本，方便 Objective 5 调用。

---

## Objective 5：汇总测试结果并撰写论文

1. **资料归档**：推荐目录结构如下，将 Objective 4 生成的 CSV/图表与 `.bk` 同步归档，便于撰写阶段直接引用：
   ```text
   docs/objectives/data/
   ├── baseline_2023-12-01/
   │   ├── baseline.bk
   │   ├── priority_run_ports.csv
   │   ├── priority_vs_baseline.png
   │   └── iperf3.log
   ├── priority_2023-12-01/
   │   ├── priority.bk
   │   ├── baseline_run_ports.csv
   │   ├── priority_vs_baseline.png
   │   └── iperf3.log
   └── classification_2023-12-01/
       └── ...
   ```
2. **分析指标**：
  - 利用 `objective3_collect_stats.py`、`objective4_collect_stats.py` 输出的 `_flows.csv`、`_tables.csv`、`_meters.csv`、`_queues.csv` 追踪各策略下关键流的 `byte_count`、`lookup_count`、`meter_byte_ps`、`queue_tx_mbps` 等指标，必要时在 pandas 中按 `cookie`/`priority`/`queue_id` 过滤。
  - 结合 `objective4_plot.py` 或 `objective5_generate_assets.py` 生成的端口吞吐、队列速率、Meter 曲线与 `iperf3` 日志中的 `Jitter`、`Lost/Total Datagrams`、`Bandwidth`，说明不同 QoS 配置对业务质量的影响；如启用 `SET_QUEUE`，需同步记录 `ovs-vsctl` 中配置的 `min-rate`、`max-rate`。
3. **撰写论文**：使用 `docs/objectives/OBJECTIVE5_REPORT_TEMPLATE.md` 作为模板，在“方法”章节插入 `flowform.html`、`meterform.html` 的截图，在“结果”章节引用 Dashboard/Stats 导出的曲线和表格，在“讨论”章节总结 QoS 策略优劣。
4. **版本管理**：将 `.bk` 配置、CSV、图表与脚本压缩或使用 Git LFS 提交至仓库，并在提交信息中注明对应 Objective 与日期，确保后续复现。

按照以上步骤，即可完全依赖 FlowManager Web UI 完成从环境搭建到结果汇总的全过程。祝研究顺利！
