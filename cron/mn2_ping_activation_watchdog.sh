#!/usr/bin/env bash
# Fast multi-ping watchdog: register new masternode.conf aliases (every 5 min).
# Stall recovery + staking unlock stay on mn2_ops_watchdog.sh (15 min).
set -euo pipefail
cd /var/www/html
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${WEB_ROOT:-/var/www/html}/logs"
mkdir -p "$LOG_DIR"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] mn2-ping-activation $*"; }

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/mn2_read_ops_secret.sh" 2>/dev/null || true
SECRET=$(mn2_read_ops_secret 2>/dev/null || true)
if [ -z "${SECRET:-}" ]; then
  log "WARN: no ops secret — skip sync-ping-targets"
  exit 0
fi

OUT=$(curl -sS -m 90 -X POST -H "X-Ops-Secret: ${SECRET}" \
  http://127.0.0.1:5000/api/mn2/masternode/sync-ping-targets 2>&1 || true)
if echo "$OUT" | grep -q '"skipped": true'; then
  log "all aliases ping-healthy (skipped)"
elif echo "$OUT" | grep -q '"success": true'; then
  log "registered ping targets: $(echo "$OUT" | head -c 240)"
else
  log "sync-ping-targets: $(echo "$OUT" | head -c 240)"
fi
