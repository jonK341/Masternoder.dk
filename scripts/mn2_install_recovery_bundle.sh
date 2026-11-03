#!/usr/bin/env bash
# pragma: allowlist secret
# Pull recovery scripts from GitHub without switching branches (keeps server hotfixes).
#
# Usage:
#   cd /var/www/html && bash scripts/mn2_install_recovery_bundle.sh
#   bash scripts/mn2_install_recovery_bundle.sh --with-backend
#
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"
WITH_BACKEND=0
BR_REF="${MN2_RECOVERY_REF:-cursor/mn2-fleet-audit-script-4e57}"

for arg in "$@"; do
  case "$arg" in
    --with-backend) WITH_BACKEND=1 ;;
    -h|--help)
      sed -n '2,7p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
  esac
done

log() { echo "[mn2-install] $*" >&2; }

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  log "ERROR: $WEB is not a git repo"
  exit 1
fi

log "fetch origin $BR_REF"
git fetch origin "$BR_REF"

REMOTE="origin/${BR_REF}"
if ! git rev-parse --verify "$REMOTE" >/dev/null 2>&1; then
  log "ERROR: missing $REMOTE after fetch"
  exit 1
fi

SCRIPT_FILES=(
  scripts/mn2_install_recovery_bundle.sh
  scripts/mn2_fleet_full_recovery.sh
  scripts/mn2_kill_all_daemons.sh
  scripts/mn2_reset_rpc_failover_primary.sh
  scripts/mn2_repair_daemon.sh
  scripts/mn2_diagnose_rpc_wallet.sh
  scripts/mn2_bring_rented_online.py
  scripts/mn2_activate_all_rented.py
  scripts/mn2_activate_all_rented.sh
  scripts/mn2_with_env.sh
  scripts/mn2_provision_status.sh
  scripts/mn2_fleet_audit.py
)

BACKEND_FILES=(
  backend/services/mn2_rpc_client.py
  backend/services/mn2_masternode_service.py
  backend/routes/mn2_masternode_routes.py
)

checkout_list=("${SCRIPT_FILES[@]}")
if [[ "$WITH_BACKEND" -eq 1 ]]; then
  checkout_list+=("${BACKEND_FILES[@]}")
fi

existing=()
for f in "${checkout_list[@]}"; do
  if git cat-file -e "$REMOTE:$f" 2>/dev/null; then
    existing+=("$f")
  else
    log "skip (not on branch): $f"
  fi
done

log "checkout ${#existing[@]} files from $REMOTE"
git checkout "$REMOTE" -- "${existing[@]}"
chmod +x scripts/mn2_*.sh 2>/dev/null || true

log "Done. Next:"
log "  kill -9 \$(pgrep -f 'mn2_bring_rented_online|mn2_start_masternode|startmasternode all') 2>/dev/null || true"
log "  export MN2_WALLET_PASSPHRASE='…'   # if wallet locked"
log "  bash scripts/mn2_fleet_full_recovery.sh"
