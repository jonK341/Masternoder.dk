#!/usr/bin/env bash
# End-to-end MN2 wallet RPC diagnosis: daemon, CLI, curl (root + www-data), app health, failover.
#
# Run on server:  cd /var/www/html && bash scripts/mn2_diagnose_rpc_wallet.sh
#
# Exit 0 only if daemon CLI + HTTP RPC + app /api/health mn2_rpc are healthy.

set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
ENV="${MN2_ENV_FILE:-${WEB}/.env}"
DATADIR="${MN2_DATADIR:-${WEB}/config}"
UNIT="${MN2_UNIT:-masternoder2d}"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
APP="${APP_BASE:-http://127.0.0.1:5000}"
FAIL_CFG="${WEB}/data/mn2_rpc_failover.json"
FAIL_STATE="${WEB}/data/mn2_rpc_failover_state.json"

log() { echo "[mn2-diagnose] $*"; }
fail=0

read_env() {
  MN2_RPC_URL=""
  MN2_RPC_USER=""
  MN2_RPC_PASSWORD=""
  [ -f "$ENV" ] || return 1
  MN2_RPC_URL=$(grep -E '^MN2_RPC_URL=' "$ENV" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"') || true
  MN2_RPC_USER=$(grep -E '^MN2_RPC_USER=' "$ENV" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"') || true
  MN2_RPC_PASSWORD=$(grep -E '^MN2_RPC_PASSWORD=' "$ENV" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"') || true
  MN2_RPC_URL="${MN2_RPC_URL:-http://127.0.0.1:${MN2_RPC_PORT:-9332}}"
}

rpc_curl() {
  local url="$1" user="$2" pass="$3" method="${4:-getblockcount}"
  curl -sS --max-time 12 -u "${user}:${pass}" \
    -d "{\"jsonrpc\":\"1.0\",\"id\":\"d\",\"method\":\"${method}\",\"params\":[]}" \
    -H 'content-type: application/json' "$url" 2>&1 || echo "CURL_ERROR"
}

section() { echo; echo "======== $* ========"; }

section "systemd ${UNIT}"
systemctl is-active "$UNIT" 2>/dev/null || echo inactive
systemctl show -p MainPID,ActiveState,SubState --value "$UNIT" 2>/dev/null | paste - - - || true
echo "masternoder2d PIDs: $(pgrep -x masternoder2d 2>/dev/null | tr '\n' ' ' || echo none)"
ss -tlnp 2>/dev/null | grep -E '9332|17646' || echo "(ports 9332/17646 not listening)"

section "CLI -datadir=${DATADIR}"
if [[ -x "$CLI" ]]; then
  if out=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1); then
    echo "getblockcount: $out"
  else
    echo "getblockcount FAILED: $out"
    fail=1
  fi
  for m in getwalletinfo getstakingstatus; do
    if out=$("$CLI" -datadir="$DATADIR" "$m" 2>&1); then
      echo "${m}: $(echo "$out" | head -c 200)"
    else
      echo "${m} FAILED: $(echo "$out" | head -c 200)"
    fi
  done
else
  log "CLI not found: $CLI"
  fail=1
fi

section ".env vs masternoder2.conf RPC"
read_env || log "missing $ENV"
conf="${DATADIR}/masternoder2.conf"
if [[ -f "$conf" ]]; then
  echo "conf rpcuser=$(grep '^rpcuser=' "$conf" | head -1 | cut -d= -f2-)"
  echo "conf rpcport=$(grep '^rpcport=' "$conf" | head -1 | cut -d= -f2-)"
  echo "conf rpcbind=$(grep '^rpcbind=' "$conf" | head -1 | cut -d= -f2-)"
else
  log "missing $conf"
  fail=1
fi
echo "env MN2_RPC_URL=${MN2_RPC_URL:-<unset>}"
echo "env MN2_RPC_USER=${MN2_RPC_USER:-<unset>}"
echo "env MN2_RPC_PASSWORD set=$([[ -n "${MN2_RPC_PASSWORD:-}" ]] && echo yes || echo no)"

section "HTTP JSON-RPC (root, .env creds)"
if [[ -n "${MN2_RPC_PASSWORD:-}" ]]; then
  body=$(rpc_curl "$MN2_RPC_URL" "$MN2_RPC_USER" "$MN2_RPC_PASSWORD" getblockcount)
  echo "getblockcount: $(echo "$body" | head -c 300)"
  if echo "$body" | grep -q '"result"'; then
    :
  else
    fail=1
  fi
  body=$(rpc_curl "$MN2_RPC_URL" "$MN2_RPC_USER" "$MN2_RPC_PASSWORD" getwalletinfo)
  echo "getwalletinfo: $(echo "$body" | head -c 300)"
else
  log "skip HTTP RPC — no MN2_RPC_PASSWORD in .env"
  fail=1
fi

section "HTTP JSON-RPC (www-data — same as uWSGI workers)"
if [[ -n "${MN2_RPC_PASSWORD:-}" ]] && id www-data &>/dev/null; then
  body=$(sudo -u www-data env MN2_RPC_URL="$MN2_RPC_URL" MN2_RPC_USER="$MN2_RPC_USER" MN2_RPC_PASSWORD="$MN2_RPC_PASSWORD" \
    bash -c 'curl -sS --max-time 12 -u "$MN2_RPC_USER:$MN2_RPC_PASSWORD" \
      -d "{\"jsonrpc\":\"1.0\",\"id\":\"w\",\"method\":\"getblockcount\",\"params\":[]}" \
      -H "content-type: application/json" "$MN2_RPC_URL"' 2>&1) || body="CURL_ERROR"
  echo "www-data getblockcount: $(echo "$body" | head -c 300)"
  if ! echo "$body" | grep -q '"result"'; then
    log "www-data cannot reach RPC — app will show wallet/RPC down even if root CLI works"
    fail=1
  fi
else
  log "skip www-data probe"
fi

section "RPC failover state (app may use standby URL)"
if [[ -f "$FAIL_CFG" ]]; then
  echo "config: $(head -c 400 "$FAIL_CFG")"
else
  echo "no $FAIL_CFG (failover disabled — OK)"
fi
if [[ -f "$FAIL_STATE" ]]; then
  echo "state: $(cat "$FAIL_STATE" 2>/dev/null | head -c 400)"
  if grep -q '"active"[[:space:]]*:[[:space:]]*"standby"' "$FAIL_STATE" 2>/dev/null; then
    log "FIX: app may be pointed at STANDBY. Reset with:"
    log "  bash scripts/mn2_reset_rpc_failover_primary.sh"
    fail=1
  fi
else
  echo "no state file (active=primary assumed)"
fi

section "Flask app /api/health mn2_rpc"
if hc=$(curl -sS --max-time 15 "${APP}/api/health" 2>&1); then
  echo "$hc" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
except Exception as e:
    print('invalid json', e); sys.exit(1)
rpc=(d.get('components') or {}).get('mn2_rpc') or {}
print(json.dumps(rpc, indent=2))
st=rpc.get('status')
sys.exit(0 if st=='healthy' else 2)
" || fail=1
else
  log "app unreachable at ${APP}/api/health"
  fail=1
fi

section "recent daemon log errors"
journalctl -u "$UNIT" -n 25 --no-pager 2>/dev/null | tail -15 || true

section "summary"
if [[ "$fail" -eq 0 ]]; then
  log "OK — daemon + HTTP RPC + app health agree"
else
  log "FAILED — see sections above"
  log "Common fixes:"
  log "  1) bash scripts/mn2_kill_all_daemons.sh"
  log "  2) systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001"
  log "  3) bash scripts/mn2_reset_rpc_failover_primary.sh  (if failover stuck on standby)"
  log "  4) grep EnvironmentFile= /etc/systemd/system/uwsgi-vidgenerator.service  # must load ${ENV}"
fi
exit "$fail"
