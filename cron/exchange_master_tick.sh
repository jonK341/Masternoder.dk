#!/bin/bash
# Exchange master daemon — one tick (platform bots, user agents, PayPal auto-sweep when ready).
# Uses flock so cron cannot stack overlapping ticks (each tick can run 5+ minutes).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export EXCHANGE_DAEMON_MODE=live
export DAEMON_QUIET=1
export EXCHANGE_PROFIT_PROFILE=max
export EXCHANGE_LIVE_PROFIT_MAX=1
export BINANCE_QUOTE=USDC
export EXCHANGE_AUTO_PAYPAL_SWEEP="${EXCHANGE_AUTO_PAYPAL_SWEEP:-1}"
export EXCHANGE_FORCE_IPV4=1
LOCK="${EXCHANGE_MASTER_LOCK:-/var/run/masternoder-exchange-master.lock}"
exec flock -n "$LOCK" python3 scripts/exchange_master_daemon.py --once
