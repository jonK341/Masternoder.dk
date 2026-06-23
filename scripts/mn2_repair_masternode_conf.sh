#!/usr/bin/env bash
# Dedupe masternode.conf: one valid line per alias (alias IP:port privkey txid vout).
# Drops malformed duplicates (missing IP:port, wrong field order, NF != 5).
#
# Usage (on server as root or www-data for read; root to restart daemon after):
#   sudo bash /var/www/html/scripts/mn2_repair_masternode_conf.sh
#   sudo bash /var/www/html/scripts/mn2_repair_masternode_conf.sh --dry-run
#   sudo bash /var/www/html/scripts/mn2_repair_masternode_conf.sh --restart
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
CONFIG="${MN2_DATADIR:-$WEB/config}"
MN_CONF="$CONFIG/masternode.conf"
UNIT="${MN2_DAEMON_UNIT:-masternoder2d}"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli -datadir=$CONFIG}"
DRY_RUN=0
DO_RESTART=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --restart) DO_RESTART=1 ;;
  esac
done

log() { echo "[repair-mn-conf] $*"; }

if [[ ! -f "$MN_CONF" ]]; then
  log "ERROR: missing $MN_CONF"
  exit 1
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
cp -a "$MN_CONF" "${MN_CONF}.bak-${ts}"
log "Backup: ${MN_CONF}.bak-${ts}"

export WEB_ROOT="$WEB"
export MN2_DATADIR="$CONFIG"
PY_ARGS="dry_run=False"
[[ "$DRY_RUN" -eq 1 ]] && PY_ARGS="dry_run=True"

RESULT="$(python3 - <<PY
import json, os, sys
sys.path.insert(0, os.environ.get("WEB_ROOT", "/var/www/html"))
from backend.services import mn2_masternode_service as mn
print(json.dumps(mn.repair_masternode_conf(${PY_ARGS})))
PY
)"

echo "$RESULT" | python3 -m json.tool 2>/dev/null || echo "$RESULT"

CHANGED="$(echo "$RESULT" | python3 -c "import json,sys; print('1' if json.load(sys.stdin).get('changed') else '0')" 2>/dev/null || echo 0)"

log "== masternode.conf after repair =="
cat "$MN_CONF"

log "== listmasternodeconf (platformmn2 txid/vout) =="
$CLI listmasternodeconf 2>/dev/null | python3 -c "
import json,sys
rows=json.load(sys.stdin)
for r in rows:
    if isinstance(r,dict) and r.get('alias')=='platformmn2':
        print(json.dumps(r, indent=2))
        break
else:
    print('(platformmn2 not found or RPC down)')
" 2>/dev/null || log "WARN: listmasternodeconf failed (daemon down?)"

if [[ "$DO_RESTART" -eq 1 && "$CHANGED" == "1" && "$DRY_RUN" -eq 0 ]]; then
  log "Restarting $UNIT to reload masternode.conf"
  systemctl restart "$UNIT"
  sec="${MN2_RPC_WAIT_SEC:-180}"
  max=$((sec / 5))
  [[ "$max" -lt 6 ]] && max=6
  for ((i = 1; i <= max; i++)); do
    if systemctl is-active --quiet "$UNIT" && $CLI getblockcount 2>/dev/null | grep -qE '^[0-9]+$'; then
      log "RPC ready"
      break
    fi
    sleep 5
  done
  if [[ -x "$WEB/scripts/mn2_fix_daemon_privkey.sh" ]]; then
    bash "$WEB/scripts/mn2_fix_daemon_privkey.sh"
  fi
fi

if [[ -x "$WEB/scripts/mn2_fix_config_permissions.sh" ]]; then
  bash "$WEB/scripts/mn2_fix_config_permissions.sh"
fi

log "Done"
