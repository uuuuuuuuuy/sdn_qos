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
    sudo ovs-vsctl del-manager || true
    sudo ovs-vsctl set-manager ptcp:6632
  else
    ovs-vsctl del-manager || true
    ovs-vsctl set-manager ptcp:6632
  fi
else
  echo "[WARN] 未找到 ovs-vsctl，无法自动开启 OVSDB 管理端口，请手动执行 'ovs-vsctl set-manager ptcp:6632'" >&2
fi

# 可选：后台自动为指定交换机写入 OVSDB 地址
if [[ "${SDN_QOS_AUTO_BIND_OVSDB:-1}" != "0" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[WARN] 未找到 python3，无法启用 OVSDB 自动绑定；请参考 README 手动写入 ovsdb_addr" >&2
  else
    export SDN_QOS_API_BASE="${SDN_QOS_API_BASE:-http://127.0.0.1:8080}"
    export SDN_QOS_OVSDB_DPIDS="${SDN_QOS_OVSDB_DPIDS:-0000000000000001 0000000000000002 0000000000000003}"
    export SDN_QOS_OVSDB_ADDR="${SDN_QOS_OVSDB_ADDR:-tcp:127.0.0.1:6632}"
    export SDN_QOS_OVSDB_TIMEOUT="${SDN_QOS_OVSDB_TIMEOUT:-180}"
    export SDN_QOS_OVSDB_POLL_INTERVAL="${SDN_QOS_OVSDB_POLL_INTERVAL:-3}"
    python3 - <<'PY' &
import json
import os
import sys
import time
import urllib.error
import urllib.request

api_base = os.environ.get("SDN_QOS_API_BASE", "http://127.0.0.1:8080").rstrip("/")
ovsdb_addr = os.environ.get("SDN_QOS_OVSDB_ADDR", "tcp:127.0.0.1:6632")
timeout = float(os.environ.get("SDN_QOS_OVSDB_TIMEOUT", "180"))
interval = float(os.environ.get("SDN_QOS_OVSDB_POLL_INTERVAL", "3"))
dpid_tokens = os.environ.get("SDN_QOS_OVSDB_DPIDS", "").split()
pending = {token.lower() for token in dpid_tokens if token.strip()}

if not pending:
    sys.exit(0)

start_ts = time.monotonic()
print(f"[INFO] 自动 OVSDB 绑定助手已启动，待处理交换机: {sorted(pending)}", file=sys.stderr)

def fetch_switches():
    try:
        with urllib.request.urlopen(f"{api_base}/stats/switches", timeout=5) as resp:
            payload = resp.read()
    except urllib.error.URLError:
        return set()
    try:
        data = json.loads(payload.decode())
    except Exception:
        return set()
    connected = set()
    for item in data:
        try:
            connected.add(f"{int(item):016x}")
        except Exception:
            continue
    return connected

def put_ovsdb(dpid: str) -> bool:
    url = f"{api_base}/v1.0/conf/switches/{dpid}/ovsdb_addr"
    data = (f'"{ovsdb_addr}"').encode()
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read()
    except urllib.error.URLError as exc:
        print(f"[WARN] 向 {dpid} 写入 OVSDB 地址失败: {exc}", file=sys.stderr)
        return False
    try:
        result = json.loads(body.decode())
    except Exception:
        return True
    if isinstance(result, dict) and result.get("result") == "failure":
        print(
            f"[WARN] 交换机 {dpid} 回应失败: {result.get('details', 'unknown')}",
            file=sys.stderr,
        )
        return False
    print(f"[INFO] 交换机 {dpid} 已写入 OVSDB 地址 {ovsdb_addr}", file=sys.stderr)
    return True

while pending:
    if time.monotonic() - start_ts > timeout:
        print(f"[WARN] 自动绑定超时，仍未处理: {sorted(pending)}", file=sys.stderr)
        break
    connected = fetch_switches()
    ready = sorted(pending & connected)
    if not ready:
        time.sleep(interval)
        continue
    for dpid in ready:
        if put_ovsdb(dpid):
            pending.discard(dpid)
    time.sleep(0.5)

if not pending:
    print("[INFO] 所有指定交换机均已完成 OVSDB 绑定", file=sys.stderr)
PY
  fi
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
