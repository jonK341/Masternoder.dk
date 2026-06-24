#!/usr/bin/env bash
# Ops watchdogs: config permissions, staking unlock, frozen ping loop.
# Install: mn2_install_watchdogs_remote.py --ask-pass
set -euo pipefail
cd /var/www/html
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${WEB_ROOT:-/var/www/html}/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] mn2-watchdog $*"; }

# 1) Config dir writable by www-data (provision atomic writes)
if [ -f scripts/mn2_fix_config_permissions.sh ]; then
  if ! bash scripts/mn2_fix_config_permissions.sh --verify >/dev/null 2>&1; then
    log "fixing config permissions"
    bash scripts/mn2_fix_config_permissions.sh >/dev/null 2>&1 || true
  fi
fi

# 2) Unlock wallet / restore staking after masternoder2d restart
PY=./venv/bin/python
[ -x "$PY" ] || PY=python3
if [ -f scripts/mn2_staking_watchdog.py ]; then
  "$PY" scripts/mn2_staking_watchdog.py 2>&1 | sed 's/^/  /' || true
fi

# 3) Ping loop stall — maintain-ping (also runs via provision cron every 2 min)
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/mn2_read_ops_secret.sh" 2>/dev/null || true
SECRET=$(mn2_read_ops_secret 2>/dev/null || true)
if [ -n "${SECRET:-}" ]; then
  PING_OUT=$(curl -sS -m 90 -X POST -H "X-Ops-Secret: ${SECRET}" \
    http://127.0.0.1:5000/api/mn2/masternode/maintain-ping 2>&1 || true)
  if echo "$PING_OUT" | grep -q '"skipped": true'; then
    log "ping loop healthy (skipped)"
  elif echo "$PING_OUT" | grep -q '"success": true'; then
    log "ping loop restarted"
  elif [ -n "$PING_OUT" ]; then
    log "maintain-ping: $(echo "$PING_OUT" | head -c 200)"
  fi
else
  log "WARN: no ops secret — skip maintain-ping"
fi

log "done"
