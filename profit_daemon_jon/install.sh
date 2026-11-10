#!/usr/bin/env bash
# Install The Profit Daemon Jon (venv + deps + top-25 technologies).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="${VENV:-$ROOT/.venv}"

echo "[The Profit Daemon Jon] install root=$ROOT"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "[install] creating venv $VENV"
  "$PYTHON_BIN" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$ROOT/profit_daemon_jon/requirements.txt"

if [[ ! -f "$ROOT/.env" && -f "$ROOT/profit_daemon_jon/.env.example" ]]; then
  cp "$ROOT/profit_daemon_jon/.env.example" "$ROOT/.env"
  echo "[install] wrote .env from profit_daemon_jon/.env.example (edit before going live)"
fi

"$VENV/bin/python" "$ROOT/profit_daemon_jon/run.py" --install-top25
"$VENV/bin/python" "$ROOT/profit_daemon_jon/run.py" --status
echo
echo "Next:"
echo "  $VENV/bin/python profit_daemon_jon/run.py --once --profile paper"
echo "  $VENV/bin/python profit_daemon_jon/run.py --sales --hours 3"
echo "  bash profit_daemon_jon/build_release.sh   # optional standalone binary"
