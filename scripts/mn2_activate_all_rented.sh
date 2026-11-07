#!/usr/bin/env bash
# One command: drain all pending rented hosts + startmasternode all (multi-ping fleet).
#
# Run after RPC is healthy (e.g. post-reboot):
#   cd /var/www/html && bash scripts/mn2_activate_all_rented.sh
#   bash scripts/mn2_activate_all_rented.sh --summary
#   bash scripts/mn2_activate_all_rented.sh --skip-drain
#
# Optional env: MN2_WALLET_PASSPHRASE (real wallet password in .env — not a placeholder)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB="${WEB_ROOT:-/var/www/html}"
if [[ ! -d "$WEB" ]]; then
  WEB="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$WEB"

log() { echo "[activate-all $(date -u +%H:%M:%S)] $*" >&2; }

LOCK_FILE="${MN2_ACTIVATE_LOCK:-$WEB/data/mn2_activate_all.lock}"
mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "ERROR: another activate-all is already running."
  log "Check: pgrep -af 'mn2_activate_all_rented'"
  log "Stop extras: kill \$(pgrep -f 'mn2_activate_all_rented' | tr '\\n' ' ')"
  exit 1
fi

log "starting pid=$$ web=$WEB args=$*"

export PYTHONUNBUFFERED=1
export MN2_RPC_HEALTH_TIMEOUT="${MN2_RPC_HEALTH_TIMEOUT:-60}"
export MN2_RPC_TIMEOUT="${MN2_RPC_TIMEOUT:-60}"
export MN2_RPC_MAX_RETRIES="${MN2_RPC_MAX_RETRIES:-2}"

if [[ -f "$WEB/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$WEB/.env"
  set +a
fi

# Wallet unlock runs inside Python (_unlock_wallet) — avoid blocking CLI walletpassphrase here.

CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
DATADIR="${MN2_DATADIR:-$WEB/config}"
if [[ -x "$CLI" ]]; then
  if out=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1) && [[ "$out" =~ ^[0-9]+$ ]]; then
    log "CLI RPC height=$out"
  elif ! out=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1) || [[ ! "$out" =~ ^[0-9]+$ ]]; then
    log "WARN: CLI RPC not ready yet: ${out:0:120}"
    log "Waiting up to 120s for getblockcount…"
    for i in $(seq 1 120); do
      if out=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1) && [[ "$out" =~ ^[0-9]+$ ]]; then
        log "RPC height=$out (after ${i}s)"
        break
      fi
      if [[ $((i % 15)) -eq 0 ]]; then
        log "still waiting RPC (${i}/120s)…"
      fi
      sleep 1
    done
  fi
fi

log "exec python3 mn2_activate_all_rented.py $*"
exec python3 "$SCRIPT_DIR/mn2_activate_all_rented.py" "$@"
