#!/bin/bash
# Exchange master daemon — one tick (platform bots, user agents, PayPal auto-sweep when ready).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export EXCHANGE_DAEMON_MODE=live
export DAEMON_QUIET=1
export EXCHANGE_PROFIT_PROFILE=max
export EXCHANGE_LIVE_PROFIT_MAX=1
export BINANCE_QUOTE=USDC
python3 scripts/exchange_master_daemon.py --once --auto-sweep
