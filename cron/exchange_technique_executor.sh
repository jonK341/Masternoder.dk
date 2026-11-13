#!/bin/bash
# Technique executor — apply pbook/hunter top-deal techniques when the unified
# profit daemon is NOT already running (daemon owns the executor loop otherwise).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if pgrep -f '[/]scripts/all_profit_daemons.py' >/dev/null 2>&1; then
  exit 0
fi

PYTHON_BIN="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

export EXCHANGE_DAEMON_MODE=live
export DAEMON_QUIET=1
export LITE_APP=1
export EXCHANGE_PROFIT_PROFILE=max
export EXCHANGE_LIVE_PROFIT_MAX=1
export BINANCE_QUOTE=USDC
export EXCHANGE_FORCE_IPV4=1
export TECH_EXECUTOR_ENABLED="${TECH_EXECUTOR_ENABLED:-1}"
export PROFIT_BOOK_APPLY="${PROFIT_BOOK_APPLY:-1}"

exec flock -n /var/run/masternoder-technique-executor.lock \
  "$PYTHON_BIN" -c 'from backend.services.exchange_technique_executor_service import run_technique_executor_tick; import json; print(json.dumps(run_technique_executor_tick(force=True), default=str))'
