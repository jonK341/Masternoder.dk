#!/bin/bash
# Venue cycle circles — one profit-estimate tick (execute only on big estimated edge).
# When masternoder-profit-daemon.service / all_profit_daemons.py is active it already
# runs a dedicated cycle-circles loop — skip cron to avoid duplicate API load.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if pgrep -f '[/]scripts/all_profit_daemons.py' >/dev/null 2>&1; then
  exit 0
fi

PYTHON_BIN="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

export DAEMON_QUIET=1
export LITE_APP=1
export EXCHANGE_FORCE_IPV4=1
export CYCLE_CIRCLES_ENABLED="${CYCLE_CIRCLES_ENABLED:-1}"
export CYCLE_CIRCLES_AUTO="${CYCLE_CIRCLES_AUTO:-1}"

exec flock -n /var/run/masternoder-cycle-circles.lock \
  "$PYTHON_BIN" scripts/venue_cycle_circles.py daemon-tick --force
