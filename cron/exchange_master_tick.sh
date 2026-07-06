#!/bin/bash
# Exchange master daemon — one tick (platform bots, user agents, PayPal auto-sweep when ready).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export EXCHANGE_DAEMON_MODE=live
export DAEMON_QUIET=1
export EXCHANGE_PROFIT_PROFILE=max
export EXCHANGE_LIVE_PROFIT_MAX=1
export BINANCE_QUOTE=USDC
export EXCHANGE_AUTO_PAYPAL_SWEEP="${EXCHANGE_AUTO_PAYPAL_SWEEP:-1}"
export EXCHANGE_FORCE_IPV4=1
# flock (-n, non-blocking) prevents overlapping ticks from piling up: on a small
# box a tick can exceed the 2-min cron interval, and without this guard each cron
# run spawns another daemon, stacking to 5+ processes that exhaust RAM/CPU and
# take the whole box down. If a tick is still running, skip this cron cycle.
# nice/ionice: the tick is CPU/IO heavy and must yield to the web app on the
# 2-core box, so page/API requests stay responsive while a tick runs.
# timeout: a healthy tick is ~15s, but a hung outbound venue fetch can leave the
# --once process stuck for many minutes, holding the lock and dragging the whole
# box down (observed 350s+). Kill any tick that exceeds 90s so it can't wedge.
exec nice -n 15 ionice -c3 \
    flock -n /run/lock/masternoder-exchange-master.lock \
    timeout --signal=KILL 90 \
    python3 scripts/exchange_master_daemon.py --once
