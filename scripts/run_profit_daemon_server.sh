#!/usr/bin/env bash
# 24/7 profit daemon runner for masternoder.dk (systemd/cron).
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  # Strip Windows CRLF so EXCHANGE_PROFIT_PROFILE=max does not become max\r (argparse exit 2).
  source <(sed 's/\r$//' "$ROOT/.env") 2>/dev/null || true
  set +a
fi

export DAEMON_QUIET="${DAEMON_QUIET:-1}"
export LITE_APP="${LITE_APP:-1}"
export EXCHANGE_DAEMON_MODE="${EXCHANGE_DAEMON_MODE:-live}"
export EXCHANGE_PROFIT_PROFILE="${EXCHANGE_PROFIT_PROFILE:-paypal}"
export EXCHANGE_LIVE_PROFIT_MAX="${EXCHANGE_LIVE_PROFIT_MAX:-0}"
export EXCHANGE_PAIR_SEARCH_MIN_INTERVAL_SEC="${EXCHANGE_PAIR_SEARCH_MIN_INTERVAL_SEC:-120}"
export PROFIT_DAEMON_NICE="${PROFIT_DAEMON_NICE:-10}"
export BINANCE_QUOTE="${BINANCE_QUOTE:-USDC}"
export EXCHANGE_FORCE_IPV4="${EXCHANGE_FORCE_IPV4:-1}"

# Rotate oversized daemon logs before start
python3 - <<'PY' "$ROOT" 2>/dev/null || true
import os, sys
sys.path.insert(0, sys.argv[1])
try:
    from backend.services.profit_daemon_ops_service import rotate_daemon_logs
    r = rotate_daemon_logs()
    if r.get("rotated"):
        print("[run] rotated logs:", r["rotated"])
except Exception:
    pass
PY

AUTO_SWEEP_ARGS=()
if [[ "${EXCHANGE_AUTO_PAYPAL_SWEEP:-0}" =~ ^(1|true|yes|on)$ ]]; then
  AUTO_SWEEP_ARGS+=(--auto-sweep)
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT/.venv/bin/python"
  elif [[ -x "$ROOT/venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT/venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

exec "$PYTHON_BIN" "$ROOT/scripts/all_profit_daemons.py" --profile "${EXCHANGE_PROFIT_PROFILE}" "${AUTO_SWEEP_ARGS[@]}"
