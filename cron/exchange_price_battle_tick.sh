#!/bin/bash
# Price battle — one tick: manage $5 hold-to-profit positions.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

export DAEMON_QUIET=1
export LITE_APP=1
export EXCHANGE_FORCE_IPV4=1

exec flock -n /var/run/masternoder-price-battle.lock \
  "$PYTHON_BIN" scripts/exchange_price_battle_daemon.py --once >> logs/price_battle_daemon.log 2>&1
