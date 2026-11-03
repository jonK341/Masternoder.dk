#!/usr/bin/env bash
# One-shot MN2 fleet + RPC + provisioning recovery (run as root on the web host). <!-- pragma: allowlist secret -->
#
# Fixes: duplicate/stuck masternoder2d, RPC read timeouts, missing MN2_OPS_SECRET,
# failover stuck on standby, config perms, wallet unlock, uWSGI env, batched provision.
#
# Usage:
#   cd /var/www/html && bash scripts/mn2_fleet_full_recovery.sh
#   bash scripts/mn2_fleet_full_recovery.sh --dry-run
#   bash scripts/mn2_fleet_full_recovery.sh --skip-provision
#   bash scripts/mn2_fleet_full_recovery.sh --provision-passes 40 --provision-limit 15
#
# Env (optional): WEB_ROOT, MN2_DATADIR, MN2_WALLET_PASSPHRASE, PROVISION_PASSES, PROVISION_LIMIT

set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=0
SKIP_PROVISION=0
PROVISION_PASSES="${PROVISION_PASSES:-25}"
PROVISION_LIMIT="${PROVISION_LIMIT:-10}"

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --skip-provision) SKIP_PROVISION=1 ;;
    --provision-passes=*) PROVISION_PASSES="${arg#*=}" ;;
    --provision-limit=*) PROVISION_LIMIT="${arg#*=}" ;;
    -h|--help)
      sed -n '2,14p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
  esac
done

log() { echo "[mn2-recover $(date -u +%H:%M:%S)] $*" >&2; }

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY: $*"
    return 0
  fi
  log "+ $*"
  "$@"
}

kill_stuck_ops_python() {
  local pid script
  for script in mn2_bring_rented_online mn2_start_masternode mn2_recover_pending; do
    while read -r pid; do
      [[ -z "$pid" || "$pid" == "$$" ]] && continue
      log "stop stuck pid $pid ($script)"
      kill -TERM "$pid" 2>/dev/null || true
    done < <(pgrep -f "scripts/${script}" 2>/dev/null || true)
  done
  sleep 2
  while read -r pid; do
    [[ -z "$pid" || "$pid" == "$$" ]] && continue
    kill -9 "$pid" 2>/dev/null || true
  done < <(pgrep -f "scripts/mn2_bring_rented_online" 2>/dev/null || true)
}

ensure_ops_secret() {
  local env="$WEB/.env"
  [[ -f "$env" ]] || { log "ERROR: missing $env"; return 1; }
  local cur
  cur=$(grep -E '^MN2_OPS_SECRET=' "$env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' || true)
  if [[ -n "${cur:-}" ]]; then
    log "MN2_OPS_SECRET already set (len ${#cur})"
    return 0
  fi
  local key val
  for key in DISCORD_OPS_SECRET ADMIN_OPS_SECRET MN2_SCAN_SECRET AGENT_CRON_SECRET; do
    val=$(grep -E "^${key}=" "$env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' || true)
    if [[ -n "${val:-}" ]]; then
      if [[ "$DRY_RUN" -eq 1 ]]; then
        log "DRY: would append MN2_OPS_SECRET from $key"
        return 0
      fi
      cp -a "$env" "${env}.bak.$(date +%s)"
      printf '\nMN2_OPS_SECRET=%s\n' "$val" >> "$env"
      log "Appended MN2_OPS_SECRET from $key (len ${#val})"
      return 0
    fi
  done
  val=$(openssl rand -hex 24 2>/dev/null || head -c 48 /dev/urandom | xxd -p -c 48)
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "DRY: would generate new MN2_OPS_SECRET"
    return 0
  fi
  cp -a "$env" "${env}.bak.$(date +%s)"
  printf '\nMN2_OPS_SECRET=%s\n' "$val" >> "$env"
  log "Generated new MN2_OPS_SECRET in .env (len ${#val}) — save this value for ops curl"
}

load_env() {
  set -a
  # shellcheck source=/dev/null
  source "$WEB/.env"
  set +a
  export MN2_RPC_HEALTH_TIMEOUT="${MN2_RPC_HEALTH_TIMEOUT:-30}"
  export MN2_RPC_TIMEOUT="${MN2_RPC_TIMEOUT:-30}"
  export MN2_RPC_MAX_RETRIES="${MN2_RPC_MAX_RETRIES:-2}"
}

wait_cli_rpc() {
  local cli="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
  local datadir="${MN2_DATADIR:-$WEB/config}"
  local i max=90 out
  for i in $(seq 1 "$max"); do
    if out=$("$cli" -datadir="$datadir" getblockcount 2>&1) && [[ "$out" =~ ^[0-9]+$ ]]; then
      log "CLI RPC ok height=$out"
      return 0
    fi
    if [[ $((i % 12)) -eq 0 ]]; then
      log "waiting CLI RPC ($i/${max}s): ${out:0:80}"
    fi
    sleep 1
  done
  log "ERROR: CLI RPC not ready after ${max}s"
  return 1
}

python_health() {
  python3 - <<PY
import json
import os
import sys
web = "${WEB}"
sys.path.insert(0, web)
os.chdir(web)
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.mn2_rpc_client import health_check
h = health_check()
print(json.dumps(h, indent=2))
sys.exit(0 if h.get("status") == "healthy" else 1)
PY
}

provision_batches() {
  local pass limit="$PROVISION_LIMIT"
  for pass in $(seq 1 "$PROVISION_PASSES"); do
    log "provision batch $pass/$PROVISION_PASSES (limit=$limit)"
    python3 - <<PY || true
import json, os, sys
sys.path.insert(0, "$WEB")
os.chdir("$WEB")
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.mn2_masternode_service import process_pending_hosts, rented_masternodes_snapshot
snap = rented_masternodes_snapshot()
pending = len(snap.get("pending") or [])
print("before pending", pending, "daemon_healthy", snap.get("daemon_healthy"))
if not snap.get("daemon_healthy"):
    print("skip batch — daemon not healthy")
    sys.exit(1)
out = process_pending_hosts(limit=int("$limit"), skip_explorer=True)
print("processed", out.get("processed"))
for r in (out.get("results") or [])[:5]:
    print(" ", r.get("host_id"), r.get("status"), (r.get("message") or r.get("error") or "")[:60])
after = rented_masternodes_snapshot()
print("after pending", len(after.get("pending") or []))
PY
    sleep 2
  done
}

log "=== MN2 fleet full recovery (WEB=$WEB) ==="

kill_stuck_ops_python

if [[ -x "$SCRIPT_DIR/mn2_kill_all_daemons.sh" ]]; then
  run bash "$SCRIPT_DIR/mn2_kill_all_daemons.sh" --wait-rpc 120
else
  log "WARN: mn2_kill_all_daemons.sh missing — manual systemctl restart masternoder2d"
  run systemctl restart masternoder2d
  sleep 20
fi

if [[ -x "$SCRIPT_DIR/mn2_reset_rpc_failover_primary.sh" ]]; then
  run bash "$SCRIPT_DIR/mn2_reset_rpc_failover_primary.sh"
fi

ensure_ops_secret
load_env

if [[ -x "$SCRIPT_DIR/mn2_fix_config_permissions.sh" ]]; then
  run bash "$SCRIPT_DIR/mn2_fix_config_permissions.sh"
fi

if [[ -x "$SCRIPT_DIR/mn2_unlock_collateral.sh" ]]; then
  run bash "$SCRIPT_DIR/mn2_unlock_collateral.sh" || true
fi

wait_cli_rpc

log "Python RPC health (timeout ${MN2_RPC_HEALTH_TIMEOUT}s):"
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "DRY: skip python health"
else
  export WEB_ROOT="$WEB"
  if ! python_health; then
    log "WARN: Python health not healthy — retry after 30s quiet RPC"
    sleep 30
    python_health || log "WARN: still unhealthy; check journalctl -u masternoder2d"
  fi
fi

run systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
sleep 8

log "uWSGI /api/health/system mn2_rpc:"
if [[ "$DRY_RUN" -eq 0 ]]; then
  curl -sS --max-time 45 "http://127.0.0.1:5000/api/health/system" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(json.dumps(d.get('components',{}).get('mn2_rpc'), indent=2))
" || true
fi

log "Collateral pool:"
if [[ "$DRY_RUN" -eq 0 ]]; then
  python3 - <<PY
import json, os, sys
web = "${WEB}"
sys.path.insert(0, web)
os.chdir(web)
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.mn2_masternode_service import list_collateral_outputs, rented_masternodes_snapshot
print(json.dumps(list_collateral_outputs(), indent=2)[:2500])
s=rented_masternodes_snapshot()
print("pending", len(s.get("pending") or []), "active", s.get("active_count"), "healthy", s.get("daemon_healthy"))
PY
fi

if [[ "$SKIP_PROVISION" -eq 0 && "$DRY_RUN" -eq 0 ]]; then
  log "=== provisioning batches ==="
  provision_batches || true
  if [[ -x "$SCRIPT_DIR/mn2_start_masternode.py" ]]; then
    log "sync multi-ping / fleet start"
    python3 "$SCRIPT_DIR/mn2_start_masternode.py" --all-from-conf || true
  fi
fi

log "=== done ==="
log "Re-check: set -a && source .env && set +a && python3 scripts/mn2_bring_rented_online.py --snapshot"
