#!/usr/bin/env bash
# One-shot cleanup: stop competing MN2 ops, delete all pending provisioning registry rows
# (keeps active masternodes). No shop refunds. Optional daemon quiet recovery + fleet ping.
#
# Usage:
#   cd /var/www/html
#   bash scripts/mn2_cleanup_provisioning_mess.sh           # dry-run preview
#   bash scripts/mn2_cleanup_provisioning_mess.sh --apply   # execute delete
#   bash scripts/mn2_cleanup_provisioning_mess.sh --apply --recover --ping
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"

APPLY=0
RECOVER=0
PING=0
KEEP_CONF=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --recover) RECOVER=1 ;;
    --ping) PING=1 ;;
    --keep-conf) KEEP_CONF=1 ;;
    -h|--help)
      sed -n '1,14p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg (use --apply, --recover, --ping, --keep-conf)" >&2
      exit 2
      ;;
  esac
done

log() { echo "[cleanup $(date +%H:%M:%S)] $*" >&2; }

if [[ -x "$WEB/scripts/mn2_stop_fleet_ops.sh" ]]; then
  log "stop fleet ops"
  bash "$WEB/scripts/mn2_stop_fleet_ops.sh" || true
fi

DELETE_ARGS=()
if [[ "$APPLY" -eq 1 ]]; then
  DELETE_ARGS+=(--apply)
fi
if [[ "$KEEP_CONF" -eq 1 ]]; then
  DELETE_ARGS+=(--keep-conf)
fi

log "delete pending provisioning hosts (dry_run=$([[ $APPLY -eq 1 ]] && echo 0 || echo 1))"
bash "$WEB/scripts/mn2_delete_provisioning_hosts.sh" "${DELETE_ARGS[@]}"

if [[ "$APPLY" -ne 1 ]]; then
  log "Dry-run only. Re-run with --apply to delete pending hosts."
  exit 0
fi

export PYTHONPATH="${WEB}${PYTHONPATH:+:$PYTHONPATH}"
if [[ -f "$WEB/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$WEB/.env"
  set +a
fi

log "snapshot after delete"
python3 <<'PY'
import json
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.mn2_masternode_service import rented_masternodes_snapshot
s = rented_masternodes_snapshot()
print(json.dumps({
    "pending": len(s.get("pending") or []),
    "active_count": s.get("active_count"),
    "daemon_healthy": s.get("daemon_healthy"),
    "by_status": s.get("by_status"),
}, indent=2))
PY

if [[ "$RECOVER" -eq 1 ]] && [[ -x "$WEB/scripts/mn2_rpc_quiet_recovery.sh" ]]; then
  log "RPC quiet recovery (reload masternode.conf)"
  bash "$WEB/scripts/mn2_rpc_quiet_recovery.sh"
fi

if [[ "$PING" -eq 1 ]] && [[ -x "$WEB/scripts/mn2_fleet_ping_only.sh" ]]; then
  log "fleet ping (background — tail /tmp/mn2-fleet-ping.log)"
  nohup bash "$WEB/scripts/mn2_fleet_ping_only.sh" > /tmp/mn2-fleet-ping.log 2>&1 &
  log "pid=$! log=/tmp/mn2-fleet-ping.log (do not Ctrl+C the daemon during ping)"
fi

log "Done. Shop orders unchanged (no refunds)."
