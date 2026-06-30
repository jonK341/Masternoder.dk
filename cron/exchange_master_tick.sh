#!/bin/bash
# Exchange master daemon — one tick (platform bots, user agents, optional PayPal sweep).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export EXCHANGE_DAEMON_MODE=live
python3 scripts/exchange_master_daemon.py --once
