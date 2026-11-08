#!/bin/bash
# One limit-order cross-venue pass. Live orders require both gates below.
# Install with cron/masternoder-cross-trade-limit.cron.d
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

export DAEMON_QUIET=1
export LITE_APP=1
export BINANCE_QUOTE=USDC
export EXCHANGE_FORCE_IPV4=1
export EXCHANGE_ARBITRAGE_LIVE=1
export EXCHANGE_CROSS_TRADE_LIVE=1

exec flock -n /tmp/masternoder-cross-trade-limit.lock \
  "$PYTHON_BIN" scripts/cross_trade_limit_tick.py
