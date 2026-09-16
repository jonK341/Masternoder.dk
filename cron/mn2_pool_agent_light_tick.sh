#!/bin/bash
# Light MN2 pool tick — seed MN2 + rebalance stables only (no heavy agent sweep).
set -euo pipefail
ROOT="${MN2_ROOT:-/var/www/html}"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
python3 "$ROOT/scripts/mn2_pool_agent_tick.py" --light
