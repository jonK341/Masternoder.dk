#!/usr/bin/env bash
# Wait for MN2 chain sync, then unlock collateral and provision pending masternodes.
# Server-side durable monitor — safe to run under nohup (single instance via pgrep).
#
# Usage:
#   nohup bash /var/www/html/scripts/mn2_sync_then_recover.sh >>/var/log/mn2_sync_recover.log 2>&1 &
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
D="-datadir=${WEB}/config"
LOG="${MN2_SYNC_RECOVER_LOG:-/var/log/mn2_sync_recover.log}"
API_BASE="${MN2_API_BASE:-http://127.0.0.1:5000}"
SYNC_TARGET="${MN2_SYNC_TARGET:-990000}"
POLL_SECS="${MN2_SYNC_POLL_SECS:-120}"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }

load_secret() {
  if [[ -f "$WEB/cron/mn2_read_ops_secret.sh" ]]; then
    # shellcheck source=/dev/null
    source "$WEB/cron/mn2_read_ops_secret.sh"
    OPS_SECRET="${MN2_OPS_SECRET:-}"
  fi
  if [[ -z "${OPS_SECRET:-}" && -f "$WEB/.env" ]]; then
    OPS_SECRET=$(grep -E '^MN2_(OPS|SCAN)_SECRET=' "$WEB/.env" | head -1 | cut -d= -f2- | tr -d '\r"')
  fi
  if [[ -z "${OPS_SECRET:-}" ]]; then
    log "ERROR: no MN2_OPS_SECRET / MN2_SCAN_SECRET in .env"
    exit 1
  fi
  export OPS_SECRET
}

rpc_blockcount() {
  local out
  out=$("$CLI" $D getblockcount 2>&1) || return 1
  echo "$out" | grep -qE '^[0-9]+$' || return 1
  echo "$out"
}

is_synced() {
  "$CLI" $D mnsync status 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('true' if d.get('IsBlockchainSynced') else 'false')
" 2>/dev/null || echo "false"
}

check_blk_corruption() {
  local bad
  bad=$(find "$WEB/config/blocks" -name 'blk*.dat' -size 0 2>/dev/null | head -5)
  if [[ -n "$bad" ]]; then
    log "WARNING: 0-byte blk files: $bad"
    return 1
  fi
  return 0
}

wait_for_sync() {
  log "=== waiting for sync (target blockcount>${SYNC_TARGET}, IsBlockchainSynced=true) ==="
  while true; do
    if ! height=$(rpc_blockcount); then
      log "RPC error on getblockcount, retry in ${POLL_SECS}s"
      sleep "$POLL_SECS"
      continue
    fi
    synced=$(is_synced)
    headers=$("$CLI" $D getblockchaininfo 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('headers','?'))" 2>/dev/null || echo "?")
    enabled=$("$CLI" $D getmasternodecount 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('enabled',0))" 2>/dev/null || echo "?")
    check_blk_corruption || true
    log "height=$height headers=$headers IsBlockchainSynced=$synced enabled=$enabled"
    if [[ "$height" -gt "$SYNC_TARGET" && "$synced" == "true" ]]; then
      log "SYNC COMPLETE at height=$height"
      return 0
    fi
    sleep "$POLL_SECS"
  done
}

run_recovery() {
  log "=== unlock collateral ==="
  bash "$WEB/scripts/mn2_unlock_collateral.sh" 2>&1 | tee -a "$LOG" || true

  log "=== provision-pending (4x GET limit=1 skip_ping=1, 75s apart) ==="
  for i in 1 2 3 4; do
    log "provision-pending attempt $i/4"
    resp=$(curl -s -w "\nHTTP_CODE:%{http_code}" -H "X-Ops-Secret: ${OPS_SECRET}" \
      "${API_BASE}/api/mn2/masternode/provision-pending?limit=1&skip_ping=1")
    code=$(echo "$resp" | grep HTTP_CODE | cut -d: -f2)
    body=$(echo "$resp" | sed '/HTTP_CODE:/d')
    if [[ "$code" == "404" || "$code" == "000" ]]; then
      resp=$(curl -s -w "\nHTTP_CODE:%{http_code}" -H "X-Ops-Secret: ${OPS_SECRET}" \
        "${API_BASE}/api/mn2/staking/ops/provision-pending?limit=1&skip_ping=1")
      code=$(echo "$resp" | grep HTTP_CODE | cut -d: -f2)
      body=$(echo "$resp" | sed '/HTTP_CODE:/d')
    fi
    log "HTTP $code: $(echo "$body" | head -c 500)"
    [[ "$i" -lt 4 ]] && sleep 75
  done

  log "=== poll enabled count ==="
  local enabled=0
  for _ in $(seq 1 30); do
    enabled=$("$CLI" $D getmasternodecount 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('enabled',0))" 2>/dev/null || echo 0)
    log "enabled=$enabled"
    [[ "$enabled" -gt 0 ]] && break
    sleep 30
  done

  if [[ "$enabled" -gt 0 ]]; then
    log "=== one maintain-ping (enabled=$enabled) ==="
    curl -s -H "X-Ops-Secret: ${OPS_SECRET}" \
      "${API_BASE}/api/mn2/staking/ops/maintain-ping" | tee -a "$LOG" || \
    curl -s -H "X-Ops-Secret: ${OPS_SECRET}" \
      "${API_BASE}/api/mn2/masternode/maintain-ping" | tee -a "$LOG"
    if [[ -f "$WEB/cron/masternoder-mn2-masternode-provision.cron.d" ]]; then
      cp "$WEB/cron/masternoder-mn2-masternode-provision.cron.d" /etc/cron.d/masternoder-mn2-masternode-provision
      chmod 644 /etc/cron.d/masternoder-mn2-masternode-provision
      rm -f /etc/cron.d/masternoder-mn2-masternode-provision.disabled 2>/dev/null || true
      log "provision cron re-enabled (enabled=$enabled)"
    fi
  else
    log "enabled still 0 — skipping maintain-ping and cron re-enable"
  fi

  height=$(rpc_blockcount 2>/dev/null || echo "?")
  synced=$(is_synced)
  mc=$("$CLI" $D getmasternodecount 2>/dev/null || echo "{}")
  log "FINAL: height=$height IsBlockchainSynced=$synced masternodecount=$mc"
  log "RECOVERY_DONE"
}

main() {
  log "mn2_sync_then_recover started (PID $$)"
  load_secret
  wait_for_sync
  run_recovery
}

main "$@"
