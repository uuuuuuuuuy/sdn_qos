# Objective 脚本说明

该目录提供用于启动控制器、加载实验拓扑以及采集/绘图的脚本，便于快速进入 FlowManager 配置流程。QoS 规则仍在 Web UI 中完成，详见 `docs/objectives/README.md`。

## 环境约定

- 默认在仓库根目录执行命令，已按照主仓库 README 配置好虚拟环境与依赖。
- 如果虚拟环境路径不是 `.venv`，可通过环境变量 `SDN_QOS_VENV` 指定。
- Ryu 控制器监听 `6653`（OpenFlow）、`8080`（REST/FlowManager），OVSDB 管理端口为 `6632`。

## 脚本一览

| 脚本 | 目的 | 使用提示 |
| --- | --- | --- |
| `objective1_start_controller.sh` | 启动集成 FlowManager、拓扑模块与 QoS REST 的 Ryu 控制器。 | 在独立终端运行，保持前台输出以便观察日志；执行时会自动调用 `ovs-vsctl set-manager ptcp:6632`（需要 `sudo` 权限）。 |
| `objective2_launch_mininet.sh` | 启动多级树形拓扑（1 核心 + 2 汇聚 + 4 主机），用于更贴近真实网络的 GUI 验证。 | 可通过环境变量 `CTRL_IP` / `CTRL_PORT` 指定远端控制器地址。 |
| `objective4_collect_stats.py` | 利用 Ryu REST 接口定时抓取多交换机端口/流统计并导出 CSV。 | 支持 `--dpid` 多次指定及 `--flow-stats` 选项，输出位于 `docs/objectives/data/`。 |
| `objective4_plot.py` | 读取上述 CSV 计算 Mbps 并绘制折线图，便于 Objective 4/5 汇报。 | 通过 `--series label=path` 添加多条曲线，`--port` 指定端口号。 |

## 典型流程

1. **启动控制器**：`./scripts/objectives/objective1_start_controller.sh`
2. **加载多级拓扑**：新终端执行 `./scripts/objectives/objective2_launch_mininet.sh`
3. **打开 FlowManager**：浏览器访问 `http://<控制器 IP>:8080/flowmanager/index.html`，根据 `docs/objectives/README.md` 完成 QoS 配置。
4. **实验采集**：在 Objective 4/5 阶段运行 `objective4_collect_stats.py` & `objective4_plot.py` 完成数据导出与绘图。

运行结束后按 `Ctrl+C` 停止脚本即可。
