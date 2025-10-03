#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# 允许用户通过环境变量覆写虚拟环境路径
if [[ -n "${SDN_QOS_VENV:-}" ]]; then
  # shellcheck disable=SC1090
  source "${SDN_QOS_VENV}/bin/activate"
elif [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1090
  source "$REPO_ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

cat <<'MSG'
=============================================
Ryu 控制器启动脚本（Objective 1/2/3 基础）
---------------------------------------------
该脚本会以 FlowManager + QoS REST 应用的组合启动 Ryu。
请在专用终端中运行，并在另一个终端中执行 Mininet 拓扑脚本。
---------------------------------------------
监听端口：6653（OpenFlow）、6632（OVSDB）、8080（FlowManager UI/REST）
=============================================
MSG

# 确保 OVSDB 管理通道开启，便于 FlowManager 的 QoS 模块连接
if command -v ovs-vsctl >/dev/null 2>&1; then
  if (( EUID != 0 )) && command -v sudo >/dev/null 2>&1; then
    sudo ovs-vsctl --if-exists del-manager
    sudo ovs-vsctl set-manager ptcp:6632
  else
    ovs-vsctl --if-exists del-manager
    ovs-vsctl set-manager ptcp:6632
  fi
else
  echo "[WARN] 未找到 ovs-vsctl，无法自动开启 OVSDB 管理端口，请手动执行 'ovs-vsctl set-manager ptcp:6632'" >&2
fi

exec ryu-manager \
  --observe-links \
  ryu.app.rest_topology \
  ryu.app.ws_topology \
  ryu.app.ofctl_rest \
  ryu.app.gui_topology.gui_topology \
  ryu.app.simple_switch_13 \
  ryu_qos_apps.rest_conf_switch \
  ryu_qos_apps.rest_qos \
  flowmanager.flowmanager
