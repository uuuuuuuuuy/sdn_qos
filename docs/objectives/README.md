# SDN QoS 项目目标执行手册

本手册聚焦于借助 FlowManager Web UI 完成项目五个阶段目标。请确保已按照仓库 README 完成依赖安装，并使用脚本启动 Ryu 控制器与 Mininet 拓扑。

## FlowManager 快速索引

下表列出了在完成各 Objective 时需要访问的页面、必须填写的字段及推荐示例值。示例以仓库提供的树形拓扑（核心交换机 `s1`、汇聚交换机 `s2/s3`、主机 `h1`-`h4`）为基准，可按实际拓扑调整。

| 菜单项（`mainmenu.js` 中的锚点文本） | 页面标题 / 主要区域 | 常用控件及其作用（界面上显示的标签文本） |
| --- | --- | --- |
| **Home** | 主页卡片 | “Switch ID(s)” 下拉用于选择监控的交换机；“Refresh Interval” 控制卡片自动刷新周期；“Ports stats”“Flow Summary” 等卡片右上角的 `↔` 可展开，`⟳` 可强制刷新，`Pause` 暂停更新以便截图 |
| **Topology** | 拓扑画布 + 右侧信息栏 | 工具条中的 “Lock Layout” 关闭后可拖拽节点；右侧列表会展示选中交换机/主机的属性（如 `IPv4 = 10.0.0.x`）；画布左上角搜索框可按名称过滤节点 |
| **Flows** | 页眉 “Flow Tables” | 顶部 “Switches” 下拉依次查看 `s1`、`s2`、`s3`；“Table Id” 默认 `0`；“Refresh” 切换数据源后手动刷新；表格列 `priority`、`cookie`、`match`、`instructions` 用于核对前一步写入的流表 |
| **Flow Control** | 页眉 “Flow Form” | “Target” 区域的 “Switch ID”“Table ID” 指定写入目标；“Flow Operation” 单选项包括 `Add`、`Modify`、`Delete` 等；“Match Fields” 表格通过 `Match Field`/`Value` 列录入匹配条件；“Instructions” 区域提供 “Goto Meter”“Apply Actions”“Write Actions”“Goto Table” 等控制；底部按钮 “Submit”“Clear” 分别提交或清空表单 |
| **Groups** | 页眉 “Group Tables” | “Switches” 下拉与 “Group Types” 下拉用于筛选；表格列出组 ID、动作桶等信息（Objective 3-4 可忽略） |
| **Group Control** | 页眉 “Group Form” | “Target” 区域选择 `Switch ID` 与 `Group ID`，`Group Operation` 指定 `Add/Modify/Delete`，`Buckets` 表格填写动作桶（若实验不涉及组，可跳过） |
| **Meter Control** | 页眉 “Meter Control” | “Target” 区域的 “Switch ID”“Meter ID” 指定 Meter；“Meter Operation” 单选项设为 `Add`；“Flags” 复选框包括 `Rate in Kbps`、`Rate in pps`、`Do Burst Size`、`Collect Statistics`；“Meter Bands” 表格填写 `Band Type`、`Rate`、`Burst Size`；顶部 “Submit”“Clear” 控制表单提交与重置 |
| **Meters** | 页眉 “Meter Tables” | “Switches” 下拉切换交换机；表格列 `meter_id`、`flags`、`bands` 用于核对当前 Meter 设置 |
| **Messages** | 页眉 “Messages” | 标签页 “Stats” 中的 “Switch”“Stat Type” 用于选择统计类型并通过 “Start/Stop” 控制采集；“Config” 标签提供 `Switch ID`、`Rest URL`、`Method`、`Data` 字段以发送 REST 请求；“Message Log” 标签显示控制器返回的通知 |
| **Configuration** | 页眉 “Configuration Backup/Restore” | “Backup” 区域的 “Select Switches” 多选框用来决定导出范围（默认包含 `--ALL--`）；“Formatted” 复选框可切换 JSON 缩进；“Save” 按钮触发备份；“Restore” 区域的 “Choose Backup File”“Restore” 控制导入 `.bk` 文件 |
| **About** | 页眉 “About FlowManager” | 展示版本信息及开源协议链接（用于引用信息即可） |

建议在浏览器中同时打开 FlowManager 多个标签页，以便在配置与监控之间快速切换。

---

## Objective 1：搭建测试环境

1. **启动控制器**：在终端运行 `./scripts/objectives/objective1_start_controller.sh`，脚本会启用 FlowManager、拓扑可视化与 QoS REST 应用，并自动开放 OVSDB 管理端口 `ptcp:6632`；首次执行可能提示输入 `sudo` 密码。
2. **确认服务可用**：等待脚本输出 `HTTP serving on http://0.0.0.0:8080`，随后在浏览器访问 `http://<控制器 IP>:8080/flowmanager/`（带末尾 `/` 可避免静态资源路径错误；若浏览器缓存旧版本，可暂时访问 `/home/index.html` 验证静态资源加载情况）。
3. **验证基础状态采集**：
   - Home 页面的 `Switch ID(s)` 下拉菜单在交换机未上线时为空，属正常现象；上线后请选择 `0000000000000001`。
   - 保持 `Refresh Interval=5` 秒，检查 `Ports stats` 与 `Flow Summary` 卡片时间戳是否更新。尚无交换机连接时会显示 “No data to display...”，即可判定 Objective 1 完成。
4. **常见排查**：Home 页菜单中的 `Messages` 链接可查看日志；若页面无法访问，请检查 8080 端口、防火墙及浏览器缓存（可按 `Ctrl+F5`）。

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
3. **拓扑确认**：刷新菜单 “Topology”（页面标题 *Topology*），应出现 `s1` 位于中心、`s2`/`s3` 分别连接 `h1/h2` 与 `h3/h4` 的结构。点击节点验证 `s1` 具备两条南向链路，主机属性面板显示 `ipv4=10.0.0.x`。
4. **流表与统计检查**：
   - 打开菜单 “Flows”（页面标题 *Flow Tables*），依次选择 `s1`、`s2`、`s3`，确认 `simple_switch_13` 为每个端口学习到 `in_port` ↔ `OUTPUT` 条目，尤其是 `s1` 上 `in_port=1` ↔ `OUTPUT:2`（指向 `s3`）。
   - 在 Home 页 “Ports stats” 中点击 `↔` 放大卡片，关注 `s1-eth1/eth2` 与 `s2-eth1` 等端口 `rx-bytes`/`tx-bytes` 随 `pingall` 增长。如需记录基线值，可点击 `Pause` 停止刷新。
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
  - **FlowManager “Messages” 页面**：切换到 `Config` 标签，依次选择 `Switch ID`，填写 `Rest URL=/v1.0/conf/switches/<dpid>/ovsdb_addr`、`Method=PUT`、`Data="tcp:127.0.0.1:6632"` 后点击 `Send`。
- **验证结果**：将 `Method` 切换为 `GET` 继续发送，或在终端运行 `curl -X GET http://127.0.0.1:8080/v1.0/conf/switches/<dpid>/ovsdb_addr`。若响应仍为空或提示 `ovs_bridge is not exists`，请确认交换机已出现在 Home 页 “Switch ID(s)” 下拉菜单中，或延长自动绑定等待时长后再次执行。

确认 OVSDB 地址生效后，再继续下表中的配置流程。

| 步骤 | 菜单项（页面标题） | UI 控件（界面标签文本） | 操作与意义 |
| --- | --- | --- | --- |
| 1 | Configuration（页眉 “Configuration Backup/Restore”） | Backup → Select Switches | 默认高亮 `--ALL--`，表示一次性导出所有交换机的 Flow/Meter/Group 配置；保持选择即可备份三台交换机。 |
|   |   | Backup → Formatted | 可选。勾选后导出的 JSON 会带缩进，便于人工阅读；未勾选时文件更紧凑，便于版本控制。 |
|   |   | Backup → Save | 点击后，`config.js` 会顺序请求 `/status?status=meters|groups|flows` 并生成 `backup_<时间戳>.bk`。浏览器会自动下载该文件。 |
|   |   | 浏览器下载文件 | 将下载的 `backup_<时间戳>.bk` 在本地重命名为 `baseline.bk`（或移动到 `docs/objectives/configs/` 目录），以便后续快速导入。 |
| 2 | Meter Control（页眉 “Meter Control”） | Target → Switch ID | 下拉选择 `0000000000000001`（核心交换机 `s1`）。该列表由 `/data?list=switches` 自动填充，仅显示当前在线的交换机。 |
|   |   | Target → Meter ID | 在数值框内输入 `1`。FlowManager 会将其作为 `meter_id` 下发到 Ryu。 |
|   |   | Meter Operation | 保持单选按钮 `Add`，表示创建新 Meter。其他选项 `Modify`、`Delete` 用于后续调整，可暂不使用。 |
|   |   | Flags | 仅勾选 `Rate in Kbps`。页面会自动取消 `Rate in pps`，确保使用 kbps 速率；同时勾选 `Do Burst Size` 以启用后续的 `Burst Size` 输入框，`Collect Statistics` 可按需勾选（默认关闭也能正常统计）。 |
|   |   | Meter Bands（首行） | 在表格首行填写：`Band Type=DROP`、`Rate=20000`、`Burst Size=5000`。`Prec Level` 对 DROP 类型无效，保持灰色即可；若需要多条 band，可点击 `+` 复制新行。 |
|   |   | Submit 按钮 | 点击页面顶部 `Submit` 发送表单，浏览器会向 `/meterform` POST JSON。底部弹出的 Snackbar 需显示 `status: success`，同时可在 “Meters” 菜单确认 `meter_id=1`。 |
| 3 | Flow Control（页眉 “Flow Form”） | Target → Switch ID / Table ID | “Switch ID” 选择 `0000000000000001`，“Table ID” 输入 `0`，确保在表 0 写入高优先级规则。 |
|   |   | Flow Operation | 保持单选按钮 `Add`，新增关键业务流。若后续需要修改，可改选 `Modify` 或 `Delete`。 |
|   |   | Match Fields 表格 | 保持 “Match Any” 复选框未勾选。首行输入 `Match Field=in_port`、`Value=1`；点击 `+` 新增三行，依次填写 `eth_type=0x0800`、`ip_proto=17`、`udp_dst=5002`。字段名称均来自浏览器提示列表，务必与后端关键字一致。 |
|   |   | Priority / Cookie | “Priority” 输入 `200`（越大越优先）；“Cookie” 数值框输入 `1`，FlowManager 会自动以十进制写入，Ryu 会在界面上显示为 `0x1`，便于区分关键业务。其余如 “Idle Timeout”“Hard Timeout” 留空即可表示常驻。 |
|   |   | Instructions → Apply Actions | 在首行输入 `Action Type=OUTPUT`，`Value=2`（`s1` 指向 `s3/h4` 的端口，可在 “Topology” 页面确认端口编号）。如需使用队列，点击 `+` 新增一行并填写 `Action Type=SET_QUEUE`，`Value={"queue_id":1}`（确保 `s1-eth2` 预先创建了队列 ID 1）。 |
|   |   | Submit 按钮 | 点击 `Submit` 后出现 “status: success” Snackbar。随后打开 “Flows” 菜单，选择 `Switches=0000000000000001`，确认出现 `priority=200`、`cookie=1` 的新条目，且 `match` 列展示上述四个匹配字段。 |
| 4 | Flow Control（页眉 “Flow Form”） | Priority 较低的普通业务 | 保留 `Switch ID=0000000000000001`、`Table ID=0`、`Flow Operation=Add`。将 “Priority” 改为 `100`；若希望专门限制 TCP，可在 `Match Fields` 新增一行 `ip_proto=6`。 |
|   |   | Match Fields / Goto Meter | `Match Fields` 至少保留 `in_port=1`、`eth_type=0x0800`，以覆盖同一路径上的常规业务；在 “Goto Meter” 数值框填写 `1`，确保普通业务流量进入上一节创建的 Meter。 |
|   |   | Instructions → Apply Actions | 与关键业务一致，首行填写 `OUTPUT` → `2`。若关键业务配置了 `SET_QUEUE`，普通业务可保持仅输出到端口，以便 Meter 执行限速。 |
|   |   | Submit + 验证 | 点击 “Submit” → Snackbar 显示 `status: success`。回到 “Flows” 页面，确认新增 `priority=100`、`meter_id=1`（在 `instructions` 中可见）的条目；在流量运行后观察 `byte_count` 随时间受限。 |
| 5 | Configuration（页眉 “Configuration Backup/Restore”） | Backup → Select Switches / Save | 重复步骤 1 的操作，保持 `--ALL--`，点击 “Save” 备份最新的 QoS 策略。下载完成后将文件重命名为 `priority.bk`（或 `classification.bk` 等），以区分不同策略快照。 |
|   |   | Restore（可选验证） | 如需验证备份有效，可在同页的 “Restore” 区域点击 “Choose Backup File” 选中 `priority.bk`，按钮 “Restore” 变为可用后点击提交，等待 Snackbar 显示 `status: success`。 |

完成后，可在 Mininet 中执行：
```bash
# 关键业务
iperf3 -s -p 5002 &  # 在 h4 上启动
iperf3 -c 10.0.0.4 -u -b 30M -t 30 -p 5002  # 在 h1 上发起

# 普通业务
iperf3 -s -p 5003 &  # 在 h4 上启动
iperf3 -c 10.0.0.4 -u -b 50M -t 30 -p 5003
```
结合 Home 页 “Ports stats” 与 “Messages” 页面 `Stats` 标签，验证关键业务吞吐保持、普通业务受限。

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
   - `classification.bk`：在菜单 “Flow Control”（页面标题 *Flow Form*）新增以下规则后备份：
     - 规则 A：`Priority=180`、`Match`：`ip_dscp=8`、`in_port=1`；`Apply Actions[0]=OUTPUT→2`。
     - 规则 B：`Priority=90`、`Match`：`tcp_dst=5001`；`Goto Meter=1`；`Apply Actions[0]=OUTPUT→2`。
     - 在菜单 “Flows”（页面标题 *Flow Tables*）中确认出现对应条目，再回到菜单 “Configuration” 执行备份并将文件命名为 `classification.bk`。
   - 建议将 `.bk` 文件与实验脚本统一放入 `docs/objectives/configs/`（手动创建目录）。
2. **执行三轮实验**：每轮实验遵循以下流程：
   1. 在菜单 “Configuration” 选择 `Switch ID=0000000000000001`，点击 “Choose Backup File” 导入目标 `.bk` 并执行 “Restore”，等待 Snackbar 提示 `status: success`。
   2. 返回 Home 页面，`Switch ID(s)` 选择 `0000000000000001`，点击卡片右上角 `⟳` 强制刷新初始统计。
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
   - 如需补充截图，可继续在 Home 页 “Ports stats” 中点击 `↔` 放大 → `Pause` 固定值后复制。
   - “Messages” 页面 `Stats` 标签：`Switch=s1`、`Stat Type=Port` 或 `Flow`，点击 `Start` 收集曲线，结束时点击 `Stop` 并通过浏览器“另存为”保存 PNG/SVG。
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
3. **撰写论文**：使用 `docs/objectives/OBJECTIVE5_REPORT_TEMPLATE.md` 作为模板，在“方法”章节插入菜单 “Flow Control” 与 “Meter Control” 页面（分别对应 *Flow Form*、*Meter Control* 页）的截图，在“结果”章节引用 Home/Stats 导出的曲线和表格，在“讨论”章节总结 QoS 策略优劣。
4. **版本管理**：将 `.bk` 配置、CSV、图表与脚本压缩或使用 Git LFS 提交至仓库，并在提交信息中注明对应 Objective 与日期，确保后续复现。

按照以上步骤，即可完全依赖 FlowManager Web UI 完成从环境搭建到结果汇总的全过程。祝研究顺利！
