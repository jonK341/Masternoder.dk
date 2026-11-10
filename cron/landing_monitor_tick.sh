#!/usr/bin/env bash
# Refresh frontpage landing monitor cache about every 5 seconds for one minute.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export LITE_APP="${LITE_APP:-1}"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi
for _ in $(seq 1 12); do
  "$PY" "$ROOT/scripts/landing_monitor_tick.py" >/dev/null || true
  sleep 5
done
