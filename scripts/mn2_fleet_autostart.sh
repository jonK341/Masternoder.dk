#!/usr/bin/env bash
# Start all masternode.conf aliases after masternoder2d is up, then kick the local ping loop.
# Install: cp to /usr/local/bin/mn2-fleet-autostart && chmod +x
# systemd: mn2-fleet-autostart.service After=masternoder2d.service
#
# activetime stays 0 without masternode=1 + working ManageStatus ping (see masternoder2.conf.example).

set -euo pipefail

DATADIR="${MN2_DATADIR:-/var/www/html/config}"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
D="-datadir=${DATADIR}"
RPC_WAIT_SEC="${MN2_RPC_WAIT_SEC:-300}"
MNSYNC_WAIT_SEC="${MN2_MNSYNC_WAIT_SEC:-600}"

log() { echo "[mn2-fleet-autostart] $*"; }

wait_rpc() {
  local i max=$((RPC_WAIT_SEC / 5))
  for ((i = 1; i <= max; i++)); do
    if "$CLI" $D getblockcount 2>/dev/null | grep -qE '^[0-9]+$'; then
      log "RPC ready height=$("$CLI" $D getblockcount)"
      return 0
    fi
    sleep 5
  done
  log "ERROR: RPC not ready after ${RPC_WAIT_SEC}s"
  return 1
}

wait_mnsync() {
  local i max=$((MNSYNC_WAIT_SEC / 10))
  for ((i = 1; i <= max; i++)); do
    if "$CLI" $D mnsync status 2>/dev/null | grep -q '"IsBlockchainSynced": true'; then
      log "mnsync OK"
      return 0
    fi
    sleep 10
  done
  log "WARN: mnsync not finished — continuing anyway"
  return 0
}

unlock_conf_collateral() {
  # Locked collateral UTXOs are invisible to startmasternode on some builds.
  local locked
  locked=$("$CLI" $D listlockunspent 2>/dev/null || true)
  if [[ -z "$locked" || "$locked" == "[]" ]]; then
    return 0
  fi
  log "Unlocking locked UTXOs before start…"
  python3 - <<'PY' "$CLI" "$DATADIR" || true
import json, subprocess, sys
cli, datadir = sys.argv[1], sys.argv[2]
raw = subprocess.check_output([cli, f"-datadir={datadir}", "listlockunspent"], text=True)
rows = json.loads(raw or "[]")
for row in rows:
    if not isinstance(row, dict):
        continue
    tx = row.get("txid")
    vout = row.get("vout")
    if tx is None or vout is None:
        continue
    subprocess.run([cli, f"-datadir={datadir}", "lockunspent", "false", json.dumps([{"txid": tx, "vout": int(vout)}])],
                     check=False, capture_output=True, text=True)
PY
}

start_aliases() {
  local aliases
  aliases=$("$CLI" $D listmasternodeconf 2>/dev/null | python3 -c "
import json,sys
try:
    rows=json.load(sys.stdin)
except Exception:
    sys.exit(0)
for r in rows:
    if isinstance(r,dict) and r.get('alias'):
        print(r['alias'])
" 2>/dev/null || true)
  if [[ -z "${aliases// }" ]]; then
    log "No aliases in masternode.conf"
    return 0
  fi
  while IFS= read -r alias; do
    [[ -z "$alias" ]] && continue
    log "startmasternode alias false $alias (named start)"
    "$CLI" $D startmasternode alias false "$alias" || true
  done <<< "$aliases"
}

start_local_ping() {
  local conf="${DATADIR}/masternoder2.conf"
  if [[ ! -f "$conf" ]] || ! grep -q '^masternode=1' "$conf"; then
    log "Skip local ping (masternode=1 not set in masternoder2.conf)"
    return 0
  fi
  if ! grep -q '^masternodeprivkey=' "$conf"; then
    log "Skip local ping (masternodeprivkey missing)"
    return 0
  fi
  log "startmasternode local false (ping loop — activetime)"
  "$CLI" $D startmasternode local false || true
}

main() {
  wait_rpc
  wait_mnsync
  unlock_conf_collateral
  start_aliases
  start_local_ping
  log "done — check: $CLI $D listmasternodes"
}

main "$@"
