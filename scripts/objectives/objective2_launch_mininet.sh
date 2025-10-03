#!/usr/bin/env bash
set -euo pipefail

CTRL_IP=${CTRL_IP:-127.0.0.1}
CTRL_PORT=${CTRL_PORT:-6653}

cat <<MSG
=============================================
多级拓扑启动脚本（Objective 2）
---------------------------------------------
默认连接控制器：${CTRL_IP}:${CTRL_PORT}
拓扑：tree,depth=2,fanout=2（1 个核心交换机 + 2 个汇聚交换机 + 4 台主机）
提示：脚本会以 root 权限运行 Mininet，请在执行前关闭可能残留的拓扑。
启动后可在 Mininet CLI 中执行 pingall/iperf 测试，
并通过浏览器访问 FlowManager 观察三交换机互联与多主机业务场景。
=============================================
MSG

exec sudo mn \
  --controller remote,ip="${CTRL_IP}",port="${CTRL_PORT}" \
  --topo tree,depth=2,fanout=2 --mac \
  --switch ovsk,protocols=OpenFlow13 \
  --link tc
