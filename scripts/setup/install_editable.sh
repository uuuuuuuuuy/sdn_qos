#!/usr/bin/env bash
# Install the FlowManager + QoS helpers as an editable package.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN=${PYTHON:-python3}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "[ERROR] Python interpreter '$PYTHON_BIN' not found." >&2
    exit 1
fi

cd "$REPO_ROOT"

echo "[INFO] Installing sdn-qos-flowmanager in editable mode using $PYTHON_BIN"
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
"$PYTHON_BIN" -m pip install --editable .

echo "[INFO] Installation complete. You can verify with:"
echo "       $PYTHON_BIN -c 'import flowmanager; print(flowmanager.__file__)'"
