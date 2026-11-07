#!/usr/bin/env bash
# Recover from RPC "Work queue depth exceeded" / couldn't parse reply — NO bulk provisioning.
#
# Run this BEFORE activate-all or fleet recovery when health shows HTTP 500 or healthy False.
#
# Usage:
#   cd /var/www/html && bash scripts/mn2_rpc_quiet_recovery.sh
#   bash scripts/mn2_rpc_quiet_recovery.sh --then-activate   # quiet recover + ping-only
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"
THEN_ACTIVATE=0

for arg in "$@"; do
  case "$arg" in
    --then-activate) THEN_ACTIVATE=1 ;;
  esac
done

log() { echo "[rpc-quiet $(date -u +%H:%M:%S)] $*" >&2; }

if [[ -x "$SCRIPT_DIR/mn2_stop_fleet_ops.sh" ]]; then
  bash "$SCRIPT_DIR/mn2_stop_fleet_ops.sh"
fi

if [[ -x "$SCRIPT_DIR/mn2_kill_all_daemons.sh" ]]; then
  bash "$SCRIPT_DIR/mn2_kill_all_daemons.sh" --fast --wait-rpc 180
else
  systemctl restart masternoder2d
fi

sleep 5

if [[ -x "$SCRIPT_DIR/mn2_reset_rpc_failover_primary.sh" ]]; then
  bash "$SCRIPT_DIR/mn2_reset_rpc_failover_primary.sh" || true
fi

export MN2_RPC_HEALTH_TIMEOUT="${MN2_RPC_HEALTH_TIMEOUT:-60}"
export MN2_RPC_TIMEOUT="${MN2_RPC_TIMEOUT:-60}"

CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
DATADIR="${MN2_DATADIR:-$WEB/config}"

log "waiting for stable CLI RPC (3 ok reads, 5s apart)…"
ok_reads=0
for i in $(seq 1 60); do
  if out=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1) && [[ "$out" =~ ^[0-9]+$ ]]; then
    ok_reads=$((ok_reads + 1))
    log "getblockcount ok ($ok_reads/3) height=$out"
    if [[ "$ok_reads" -ge 3 ]]; then
      break
    fi
    sleep 5
  else
    ok_reads=0
    if [[ $((i % 6)) -eq 0 ]]; then
      log "waiting… (${i}/60) ${out:0:80}"
    fi
    sleep 5
  fi
done

if [[ "$ok_reads" -lt 3 ]]; then
  log "ERROR: RPC not stable — check: journalctl -u masternoder2d -n 50 --no-pager"
  exit 1
fi

log "wallet warm-up 90s (avoid listunspent while loading)…"
sleep 90

systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>/dev/null || true
sleep 10

log "light health (getblockcount only):"
set -a
# shellcheck source=/dev/null
[[ -f "$WEB/.env" ]] && source "$WEB/.env"
set +a
python3 - <<PY
import json, os, sys
web = "${WEB}"
sys.path.insert(0, web)
os.chdir(web)
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.mn2_rpc_client import health_check
print(json.dumps(health_check(), indent=2))
PY

log "Done. Next (one at a time):"
log "  bash scripts/mn2_activate_all_rented.sh --skip-drain --summary --progress"
log "  bash scripts/mn2_activate_all_rented.sh --summary --progress --batch-size 5"

if [[ "$THEN_ACTIVATE" -eq 1 ]]; then
  log "running ping-only activate…"
  bash "$SCRIPT_DIR/mn2_activate_all_rented.sh" --skip-drain --summary --progress
fi
