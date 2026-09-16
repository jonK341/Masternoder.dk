#!/bin/bash
set -euo pipefail
ROOT="${MN2_ROOT:-/var/www/html}"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
python3 "$ROOT/scripts/agent_sweeper_tick.py"
