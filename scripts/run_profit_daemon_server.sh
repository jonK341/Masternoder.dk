#!/usr/bin/env bash
# 24/7 profit daemon runner for masternoder.dk (systemd/cron).
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi

export DAEMON_QUIET="${DAEMON_QUIET:-1}"
export LITE_APP="${LITE_APP:-1}"
export EXCHANGE_DAEMON_MODE="${EXCHANGE_DAEMON_MODE:-live}"
export EXCHANGE_PROFIT_PROFILE="${EXCHANGE_PROFIT_PROFILE:-max}"
export EXCHANGE_LIVE_PROFIT_MAX="${EXCHANGE_LIVE_PROFIT_MAX:-1}"
export BINANCE_QUOTE="${BINANCE_QUOTE:-USDC}"
export EXCHANGE_FORCE_IPV4="${EXCHANGE_FORCE_IPV4:-1}"

AUTO_SWEEP_ARGS=()
if [[ "${EXCHANGE_AUTO_PAYPAL_SWEEP:-0}" =~ ^(1|true|yes|on)$ ]]; then
  AUTO_SWEEP_ARGS+=(--auto-sweep)
fi

exec python3 "$ROOT/scripts/all_profit_daemons.py" --profile "${EXCHANGE_PROFIT_PROFILE}" "${AUTO_SWEEP_ARGS[@]}"
