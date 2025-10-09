# SDN QoS 项目目标执行手册

本手册聚焦于借助 FlowManager Web UI 完成项目五个阶段目标。请确保已按照仓库 README 完成依赖安装，并使用脚本启动 Ryu 控制器与 Mininet 拓扑。

## FlowManager 页面与控件详解

本节按照左侧菜单栏显示的顺序，对 FlowManager 每个页面的标题、控件标签与交互逻辑进行逐项说明，确保阅读时能与浏览器界面逐字对应。页面之间共享同一套菜单导航（位于 `flowmanager/js/mainmenu.js`），每个页面的 `Submit`/`Refresh` 等按钮都会触发相应的 REST 调用或重新绘制。

### Home（菜单链接 “Home”，页面抬头 “RYU Flow Manager v.1.0.0”）

- **“Switch ID(s)” 卡片**：位于页面左上角，逐行列出当前在线交换机的 64 位 DPID（十进制）。点击任意 DPID 会令其高亮，并触发其他卡片重新向控制器请求该交换机的统计数据。如果尚无交换机接入，该卡片显示 “No data to display...”。
- **“Switch Desc” 卡片**：展示 `Manufacturer`, `Hw Desc`, `Sw Desc`, `Serial Num`, `Dp Desc` 等描述字段，内容来自 `GET /data?switchdesc=<dpid>` 的 JSON。用于核对交换机厂商信息或验证是否连接到预期的 OVS 实例。
- **“Port Desc” 卡片**：列出交换机所有端口的配置（Port No、Hw Addr、Name、State 等），用于检查端口是否处于 `up` 状态以及端口名是否符合预期。
- **“Ports stats” 卡片**：按端口显示 `TX/RX Packets`、`TX/RX Bytes`、错误计数等实时统计。右上角的 `↔` 图标可以将卡片展开至全宽，便于截屏；`−` 图标可以折叠内容仅保留标题栏。
- **“Flow Summary” 卡片**：显示当前交换机按表汇总的流条目数量与匹配统计（字段与 Ryu `aggregate_flow_stats` 相同），可快速判断是否写入了新流表。
- **“Table stats” 卡片**：每张表的容量与当前条目数（Active Count、Lookup Count、Matched Count），用于监控表资源占用。如果控制器启用了额外模块，页面也会追加更多卡片；若未启用，对应卡片保持空白。

### Flows（菜单链接 “Flows”，页面抬头 “Flow Tables”）

- **“Refresh” 按钮**：位于标题栏右侧，手动重新请求 `GET /data?flows=<dpid>` 结果。FlowManager 默认不会自动轮询，因此每次写入流表后请点击刷新以获取最新数据。
- **顶部页签**：自动生成 `SW_1`、`SW_2` 等标签（`Tabs('switches')`），与 “Switch ID(s)” 卡片所列的 DPID 对应。切换页签即切换当前查看的交换机。
- **流表卡片**：每张表会生成一张“Flow Table”卡片。表格列标题与 FlowManager 的 `header_of13` 定义一致，包括 `Priority`、`Match Fields`、`Cookie`、`Duration`、`Idle Timeout`、`Hard Timeout`、`Instructions`、`Packet Count`、`Byte Count`、`Flags`。这些字段直接反映 `dump_flows` 结果，便于核对 Flow Control 表单提交后的效果。
- **行选择器**：左侧复选框可勾选若干流项，供后续调用 “Messages → Stats” 里的监控功能；默认教程不依赖该功能，但可以用来定位具体条目。

### Groups（菜单链接 “Groups”，页面抬头 “Group Tables”）

- **页签 “Group Types”**：按交换机生成标签，并在每个标签内进一步分 `all / select / indirect / fast_failover` 四个子表，列出组 ID、引用端口及动作桶。若控制器尚未安装组表，页面显示空白提示。
- **“Refresh” 按钮**：与 Flows 页面相同，用于手动刷新 `GET /data?groups=<dpid>` 的结果。

### Meters（菜单链接 “Meters”，页面抬头 “Meter Tables”）

- **页签结构**：与 “Flows” 页面一致，按交换机分组显示。每张表展示 `meter_id`、`flags`、`bands`、`band_type`、`rate`、`burst_size` 等字段，来源于 `GET /data?meters=<dpid>`。
- **统计列含义**：`flags` 列会列出 `KBPS`、`BURST`、`STATS` 等标志，`bands`/`band_type` 展示每个 band 的动作类型与速率设置，便于确认 Meter Control 表单是否生效。

### Flow Control（菜单链接 “Flow Control”，页面抬头 “Flow Form”）

- **顶部按钮**：`Submit` 将表单序列化为 JSON 并 POST `/flowform`，底部 `#snackbar` 弹出 “status: success” 或错误信息；`Clear` 使用浏览器原生的重置逻辑清空所有输入。
- **“Target” 字段集**：`Switch ID` 下拉列出所有在线交换机（值为 DPID），`Table ID` 数字输入指定要写入的表号（默认 `0`）。
- **“Flow Operation” 单选组**：提供 `Add`、`Modify`、`Modify Strict`、`Delete`、`Delete Strict` 五种 OpenFlow 操作。选择 `Delete*` 会自动启用下方的 `Output Port` / `Output Group`，允许输入 `-1` 代表 “ANY”。
- **“Match Fields” 区域**：`Match Any` 复选框勾选后等价于写入通配规则；未勾选时可在表格中通过 `Match Field`（带 datalist 自动补全）与 `Value`（文本框）逐项添加匹配条件。点击 `+` 会复制当前行并改成 `-`，用于添加或删除额外字段。
- **“Priority / Timeout / Cookie” 区域**：提供 `Priority`、`Idle Timeout`、`Hard Timeout`、`Cookie`、`Cookie Mask` 输入框。留空表示采用控制器默认值（0 或永久）。
- **“Instructions” 区域**：
  - `Goto Meter` 数字输入框：填写 Meter ID（-1 表示不引用）。
  - `Apply Actions` / `Write Actions` 表格：通过 `Action Type`（带自动补全）与 `Value` 字段配置 `OUTPUT:port`、`SET_QUEUE:{"queue_id":1}` 等动作，`+`/`-` 控制行数。
  - `Clear Actions` 复选框：勾选后会在 JSON 中加入 `clear_actions`。
  - `Write Metadata` 与 `Metadata Mask`：写入控制平面元数据，接受十进制或带 `0x` 前缀的数值。
  - `Goto Table`：指定后续跳转的表号（>=1）。
- **“Flags” 区域**：包含 `Send flow-removed msg`、`Check overlapping`、`Reset counts`、`Do not count packets`、`Do not count bytes` 五个勾选项，分别对应 OpenFlow `OFPFF_*` 标志。
- **提交结果**：成功后可在 “Flows” 页面看到新增条目；若 JSON 校验失败（由 `flowmodvalidate.js` 判定），Snackbar 会提示缺失字段或非法值。

### Group Control（菜单链接 “Group Control”，页面抬头 “Group Control”）

- **“Target” 字段集**：`Switch ID` 下拉、`Group ID` 数字输入（>0）、`Group Type` 下拉（`ALL` / `SELECT` / `INDIRECT` / `FAST_FAILOVER`）。
- **“Group Operation” 单选组**：提供 `Add`、`Modify`、`Delete`。
- **“Action Buckets” 表格**：默认渲染三块 `Bucket_1/2/3`，每块包含 `Action Type`（带 datalist）与 `Value`，用于定义该桶内的动作序列。点击 `+`/`-` 可增删同一桶内的动作。若某桶留空，提交时对应列表为空数组。
- **提交行为**：`Submit` 会向 `/groupform` POST JSON，Snackbar 返回结果字符串；`Clear` 清空所有输入并恢复默认。

### Meter Control（菜单链接 “Meter Control”，页面抬头 “Meter Control”）

- **“Target” 字段集**：`Switch ID` 下拉选择交换机，`Meter ID` 数字输入（范围 `1`~`4294901760`）。
- **“Flags” 复选框**：`Rate in Kbps`（默认勾选）与 `Rate in pps` 互斥；`Do Burst Size` 决定是否启用 `Burst Size` 输入框；`Collect Statistics` 控制是否设置 `STATS` 标志。
- **“Meter Operation” 单选组**：`Add`、`Modify`、`Delete` 对应 OpenFlow Meter 操作。
- **“Meter Bands” 表格**：首行提供 `Band Type`（datalist 包含 `DROP`、`DSCP_REMARK`）、`Rate`、`Burst Size`、`Prec Level` 四列。`+` 可复制一行用于创建额外 band，`DSCP_REMARK` 时 `Prec Level` 输入框自动启用。`Do Burst Size` 勾选后 `Burst Size` 输入框自动解除灰化。
- **提交行为**：向 `/meterform` POST JSON，响应写入 Snackbar。成功后可以在 “Meters” 页面验证 `meter_id`、`bands` 等字段。

### Topology（菜单链接 “Topology”，页面抬头 “Topology”）

- **模式页签**：顶部的 `Graph` 与 `Tables` 标签由 `Tabs('topology')` 创建。`Graph` 展示 D3 力导向图；`Tables` 以表格列出原始 JSON。
- **“Refresh” 按钮**：重新请求 `GET /topology`，以便在拓扑变动后更新画布。
- **图形交互**：
  - 节点图标分别对应交换机（`/home/img/switch.svg`）、主机（`/home/img/pc.svg`）和云节点；悬停时在左上角弹出 tooltip，显示 `dpid`、`mac`、`ipv4` 等属性。
  - 链路上方的数字显示 `src.port_no` / `dst.port_no`，方便核对 “Flow Control” 表单中使用的端口号。
  - 画布支持拖拽节点并自动保持在边界内（`box_force`）。
- **信息面板**：页面底部会打印 `/topology` 的 JSON 响应，便于排查主机缺失问题。

### Messages（菜单链接 “Messages”，页面抬头 “Messages”）

- **标签页 “Stats”**：`Switch` 下拉选择交换机，`Stat Type` 选择 `Flow`/`Port`/`Queue` 等类别，`Start`/`Stop` 控制后台轮询，结果以折线图或表格显示。
- **标签页 “Config”**：提供 `Switch ID`、`Rest URL`、`Method`（GET/PUT/POST/DELETE）、`Data` 文本框，可直接向控制器发送 REST 请求。提交结果显示在下方 `Response` 框，并自动追加到 `Message Log`。
- **标签页 “Message Log”**：展示之前的 REST 交互记录，支持滚动查看历史结果。

### Configuration（菜单链接 “Configuration”，页面抬头 “Configuration Backup/Restore”）

- **“Backup” 区域**：`Select Switches` 多选框默认高亮 `--ALL--`，表示导出所有交换机的 Flow/Meter/Group 配置；如需仅备份单台，可取消 `--ALL--` 并勾选特定 DPID。`Formatted` 复选框控制备份文件是否带缩进。`Save` 按钮会下载 `.bk` 文件并在页面底部文本框显示 JSON 内容。
- **“Restore” 区域**：点击 `Choose Backup File` 选择 `.bk` 文件后，右侧 `Restore` 按钮变为可用。提交后 FlowManager 会依次将文件中的 meters/groups/flows 写回交换机，结果写入 Snackbar。
- **文本框 `#confcontent`**：实时显示最近一次备份或上传文件的 JSON 内容，便于核对条目。

### About（菜单链接 “About”，页面抬头 “About FlowManager”）

- 展示 FlowManager 版本号、作者信息、开源协议链接，无交互控件。可用于引用原作者或确认许可证条款。

> 提示：FlowManager 页面默认 15 秒轮询一次所选交换机（`moduleManager` 的默认值）。如果需要截屏或比对数据，可先点击卡片右上角的 `−` 暂停内容更新，再使用 `↔` 展开卡片以获取更清晰的表格。

建议在浏览器中为常用页面（Home、Flow Control、Flows、Meter Control、Meters、Topology）分别打开标签页，便于在配置后立即切换到监控页面确认效果。

---

## Objective 1：搭建测试环境

1. **启动控制器**：在终端运行 `./scripts/objectives/objective1_start_controller.sh`，脚本会启用 FlowManager、拓扑可视化与 QoS REST 应用，并自动开放 OVSDB 管理端口 `ptcp:6632`；首次执行可能提示输入 `sudo` 密码。
2. **确认服务可用**：等待脚本输出 `HTTP serving on http://0.0.0.0:8080`，随后在浏览器访问 `http://<控制器 IP>:8080/flowmanager/`（带末尾 `/` 可避免静态资源路径错误；若浏览器缓存旧版本，可暂时访问 `/home/index.html` 验证静态资源加载情况）。
3. **验证基础状态采集**：
   - Home 页面的 `Switch ID(s)` 下拉菜单在交换机未上线时为空，属正常现象；上线后请选择 `0000000000000001`。
   - 在 “Switch ID(s)” 卡片点选 `0000000000000001` 后，确认 “Ports stats”“Flow Summary” 卡片的时间戳随轮询更新；若交换机尚未上线，卡片会停留在 “No data to display...”，此时等待握手完成即可。
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

### 步骤 1：在菜单 “Configuration” 备份初始基线

1. 打开左侧菜单 “Configuration”（页面标题 “Configuration Backup/Restore”）。
2. 在 “Backup” 区域保持 `Select Switches` 多选框的 `--ALL--` 选中状态，表示一次性导出所有在线交换机的 Flow/Meter/Group 配置。
3. 点击 “Save” 后，浏览器会自动下载 `backup_<时间戳>.bk`；如需固定文件名，可在本地重命名为 `baseline.bk`。同时底部文本框 `confcontent` 会从 “No content...” 更新为备份 JSON，方便现场核对内容。

### 步骤 2：在 “Meter Control” 页面创建关键业务 Meter

1. 打开菜单 “Meter Control”（页面抬头 “Meter Control”）。
2. 在 “Target” 区域：
   - `Switch ID` 下拉选择 `SW_1`（提交时会写成 DPID `0000000000000001`）。
   - `Meter ID` 输入 `1`，为关键业务预留编号。
3. 在 “Flags” 区域：
   - 保持 `Rate in Kbps` 勾选（FlowManager 会自动取消 `Rate in pps`）。
   - 勾选 `Do Burst Size` 以启用表格中的 `Burst Size` 输入。
   - `Collect Statistics` 可按需勾选（对统计展示非必需）。
4. 在 “Meter Operation” 保持单选按钮 `Add`。
5. 在 “Meter Bands” 表格首行填写：
   - `Band Type=DROP`。
   - `Rate=20000`（对应 20 Mbps，可按实验需求调整）。
   - `Burst Size=5000`（若 `Do Burst Size` 选中，输入框已可编辑）。
   - `Prec Level` 对 DROP 无效，保持灰色 `0` 即可。
   - 如需额外 Band，点击 `+` 复制新行，`-` 则删除行。
6. 点击顶部 `Submit`，等待底部 Snackbar 弹出 `status: success`。随后可切换到 “Meters” 菜单确认 `meter_id=1`、`flags=KBPS|BURST`、`bands` 等字段确实写入。

### 步骤 3：在 “Flow Control” 页面写入关键业务流

1. 打开菜单 “Flow Control”（页面抬头 “Flow Form”）。
2. 在 “Target” 区域选择 `Switch ID=0000000000000001`，`Table ID=0`（默认表）。
3. “Flow Operation” 保持 `Add`。
4. 在 “Match Fields” 表格中：
   - 确认 “Match Any” 复选框未勾选。
   - 首行填写 `Match Field=in_port`、`Value=1`（来自 `s2` 的入端口）。
   - 点击 `+` 新增三行，依次填写 `eth_type=0x0800`、`ip_proto=17`、`udp_dst=5002`。字段名称需与自动补全候选一致，以匹配 Ryu 解析逻辑。
5. 在 “Priority / Timeout / Cookie” 区域：
   - `Priority` 输入 `200`，提升关键业务优先级。
   - `Cookie` 输入 `1`，用于后续过滤该流；其余超时字段留空代表永久。
6. 在 “Instructions” 区域：
   - `Goto Meter` 留空（关键业务不走 Meter）。
   - `Apply Actions` 首行填写 `Action Type=OUTPUT`、`Value=2`（`s1` 指向 `s3/h4` 的端口号，可在 Topology 页面核对）。
   - 如需强制走队列，可再添加一行 `SET_QUEUE` 并输入 `{"queue_id":1}`（需提前在 `s1-eth2` 创建队列 1）。
   - 其他选项保持默认。
7. 点击 `Submit`。Snackbar 显示 `status: success` 后，切换到 “Flows” 页面 → 选择 `SW_1`，确认表 0 中新增 `priority=200`、`cookie=1`、`match` 列含四个字段的新条目。

### 步骤 4：写入普通业务流并挂接 Meter

1. 仍在 “Flow Control” 页面：保持 `Switch ID=0000000000000001`、`Table ID=0`、`Flow Operation=Add`。
2. 将 “Priority” 调整为 `100`，以低于关键业务。
3. 在 “Match Fields” 中保留 `in_port=1`、`eth_type=0x0800`，必要时补充 `ip_proto=6`（若要额外限制 TCP）。
4. 在 “Goto Meter” 输入 `1`，让普通业务流量进入步骤 2 创建的 Meter。
5. 在 “Apply Actions” 保持 `OUTPUT` → `2`；如关键业务使用了 `SET_QUEUE`，普通业务可不设置队列以便 Meter 控速生效。
6. 点击 `Submit` 并观察 Snackbar 成功提示。随后在 “Flows” 页面检查表项，确认 `instructions` 字段包含 `meter_id=1`，且在业务运行后 `byte_count` 受限于 Meter 设置。

### 步骤 5：再次备份策略并验证恢复

1. 回到 “Configuration” 页面，重复步骤 1 中的备份流程，点击 `Save` 下载最新策略，建议命名为 `priority.bk`（或其他具有标识性的文件名）。
2. （可选）在同一页面 “Restore” 区域点击 `Choose Backup File` 选中刚才的 `priority.bk`，待 `Restore` 按钮高亮后点击提交，确认 Snackbar 返回 `status: success`，以验证备份文件可成功恢复。

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
