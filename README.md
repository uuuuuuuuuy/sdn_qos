# 基于 Ryu + FlowManager 的 SDN QoS 管理实验平台

本仓库源自硕士论文项目，现已拓展为围绕 FlowManager 图形界面与 Ryu QoS 扩展的完整实验平台。通过 Mininet 仿真网络、Ryu 控制器与 FlowManager 交互界面，可验证按流/按分类的 QoS 保障方案，并产出可用于论文写作的实验数据与图表。

## 功能亮点

- **可视化控制**：集成 FlowManager UI、拓扑可视化与 REST 接口，便于实时查看拓扑、流表、端口统计信息。
- **Web UI 配置流程**：提供以 FlowManager 为核心的目标执行指南，可直接在浏览器内完成 Meter、队列与流表管理。
- **数据采集支持**：利用 FlowManager 页面或配套脚本导出端口/流表统计，满足对比实验需求。
- **自动化图表生成**：提供从 REST 接口导出 CSV 并用 Python 生成 Mbps 折线图的工具链，加速 Objective 4/5 的结果整理。
- **论文支撑材料**：整理实验流程、模板与常见问题，方便撰写技术报告或论文。

## 仓库结构概览

```text
sdn_qos/
├── flowmanager/               # FlowManager 应用源码（已整合至 Ryu）
├── ryu_qos_apps/              # QoS REST 与示例交换机扩展
├── scripts/
│   ├── objectives/            # 启动控制器/拓扑/采集的辅助脚本及说明
│   └── ...                    # 其他历史脚本
├── topology/                  # 数据中心及最小拓扑示例
├── demo_results/              # 实验示例输出与对比图
├── docs/objectives/           # 各阶段目标的执行手册与论文模板
└── README.md                  # 当前文件
```

## 快速开始

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
6. **注册 OVSDB 地址**：
   - 启动控制器与拓扑后，需为树形拓扑中的每台交换机（示例 DPID：`0000000000000001`、`0000000000000002`、`0000000000000003`）写入 OVSDB 地址，以便 `rest_qos` 成功建立 `OVSBridge`。可以在终端执行：
     ```bash
     for dpid in 0000000000000001 0000000000000002 0000000000000003; do
       curl -X PUT \
         http://127.0.0.1:8080/v1.0/conf/switches/${dpid}/ovsdb_addr \
         -d '"tcp:127.0.0.1:6632"'
     done
     ```
   - 或在 FlowManager `Messages` 页面的 `Config` 标签选择对应 `Switch ID`，`Rest URL=/v1.0/conf/switches/<dpid>/ovsdb_addr`，`Method=PUT`，`Data` 填写 `"tcp:127.0.0.1:6632"` 并依次提交。
   - 可通过同一页面切换到 `Method=GET`，或运行 `curl -X GET http://127.0.0.1:8080/v1.0/conf/switches/<dpid>/ovsdb_addr` 验证返回值是否为 `"tcp:127.0.0.1:6632"`。若遗漏该步骤，FlowManager 调用 QoS 功能时会收到 `result: failure, details: ovs_bridge is not exists` 的错误提示。

完成以上步骤后，即可使用 `scripts/objectives` 中的脚本启动控制器与树形拓扑，并按照 `docs/objectives/README.md` 在 FlowManager 内完成全部配置与数据采集。

## FlowManager 操作入口

- 启动控制器：`./scripts/objectives/objective1_start_controller.sh`（自动执行 `ovs-vsctl --if-exists del-manager` 与 `ovs-vsctl set-manager ptcp:6632`，首次运行需具备 `sudo` 权限）
- 启动树形拓扑：`./scripts/objectives/objective2_launch_mininet.sh`
- 浏览器访问：`http://<控制器 IP>:8080/flowmanager/index.html`
- 详细的 FlowManager 页面与字段说明：`docs/objectives/README.md`
- 自动导出 CSV：`python scripts/objectives/objective4_collect_stats.py ...`
- 绘制对比图表：`python scripts/objectives/objective4_plot.py ...`

## 目标执行指南

为便于项目管理，仓库提供了中文执行手册：

- `docs/objectives/README.md`：针对 Objective 1-5 的 FlowManager 操作步骤、页面字段取值与常见问题（含 Dashboard/Meter/Flow Form 字段填写示例）。
- `docs/objectives/OBJECTIVE5_REPORT_TEMPLATE.md`：论文写作提纲，涵盖架构说明、实验设计、结果分析与总结。

## 示例成果

仓库 `demo_results/` 下保留了原论文中的部分示例图，包括 Ryu 架构、Per-flow/DiffServ 测试结果以及 FlowManager UI 截图，可作为实验结果的参考样式。

## 许可证与联系方式

- 许可证：开源软件（保留原作者版权声明）。
- 联系方式：Amir Ashoori（a.ashoori7@gmail.com）。
- 若在复现过程中遇到问题，欢迎在 Issues 中反馈或结合文档中的常见问题排查。

祝顺利完成 Objective 1-5 并写出高质量论文！
