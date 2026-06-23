#!/usr/bin/env bash
# Ensure HTTP JSON-RPC is enabled in the daemon datadir config.
# CLI works via .cookie IPC without server=1; uwsgi/mn2_rpc_client needs server=1 + rpcbind.
#
# Usage (on server as root):
#   bash /var/www/html/scripts/mn2_ensure_rpc_conf.sh
#   bash /var/www/html/scripts/mn2_ensure_rpc_conf.sh --restart-daemon
#   bash /var/www/html/scripts/mn2_ensure_rpc_conf.sh --user=mn2rpc --password='secret' --restart-daemon
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
CONFIG="${MN2_DATADIR:-$WEB/config}"
DCONF="$CONFIG/masternoder2.conf"
ENV="${ENV_FILE:-$WEB/.env}"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli -datadir=$CONFIG}"
UNIT="${MN2_DAEMON_UNIT:-masternoder2d}"
RESTART_DAEMON=0
RPC_USER=""
RPC_PASS=""

for arg in "$@"; do
  case "$arg" in
    --restart-daemon) RESTART_DAEMON=1 ;;
    --user=*) RPC_USER="${arg#*=}" ;;
    --password=*) RPC_PASS="${arg#*=}" ;;
    --help|-h)
      echo "Usage: $0 [--restart-daemon] [--user=USER] [--password=PASS]"
      exit 0
      ;;
  esac
done

log() { echo "[ensure-rpc] $*"; }

read_env_kv() {
  local key="$1"
  [[ -f "$ENV" ]] || return 1
  grep "^${key}=" "$ENV" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"'"'"' '
}

if [[ ! -f "$DCONF" ]]; then
  log "ERROR: missing $DCONF"
  exit 1
fi

if [[ -z "$RPC_USER" ]]; then
  RPC_USER="$(read_env_kv MN2_RPC_USER || true)"
fi
if [[ -z "$RPC_PASS" ]]; then
  RPC_PASS="$(read_env_kv MN2_RPC_PASSWORD || true)"
fi
RPC_USER="${RPC_USER:-mn2rpc}"

if [[ -z "$RPC_PASS" ]]; then
  log "ERROR: rpcpassword empty — set MN2_RPC_PASSWORD in $ENV or pass --password="
  exit 1
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
cp -a "$DCONF" "${DCONF}.bak-${ts}"
log "Backup: ${DCONF}.bak-${ts}"

python3 - "$DCONF" "$RPC_USER" "$RPC_PASS" <<'PY'
import re
import sys

path, user, passwd = sys.argv[1], sys.argv[2], sys.argv[3]
rpc_keys = {"server", "rpcuser", "rpcpassword", "rpcport", "rpcbind", "rpcallowip"}

with open(path, encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()

kept = []
for line in lines:
    m = re.match(r"^(\w+)=", line)
    if m and m.group(1) in rpc_keys:
        continue
    kept.append(line)

block = [
    "server=1",
    f"rpcuser={user}",
    f"rpcpassword={passwd}",
    "rpcport=9332",
    "rpcbind=127.0.0.1",
    "rpcallowip=127.0.0.1",
]

idx = 0
while idx < len(kept) and (not kept[idx].strip() or kept[idx].lstrip().startswith("#")):
    idx += 1

out = kept[:idx] + block + kept[idx:]
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print(f"patched {path} ({len(block)} RPC lines)")
PY

log "== RPC lines in $DCONF =="
grep -E '^(server|rpcport|rpcbind|rpcallowip|rpcuser)=' "$DCONF"
grep '^rpcpassword=' "$DCONF" | sed 's/=.*/=<set>/'

if ! grep -q '^server=1' "$DCONF" || ! grep -q '^rpcuser=' "$DCONF" || ! grep -q '^rpcpassword=' "$DCONF"; then
  log "ERROR: RPC block verification failed"
  exit 1
fi
log "OK RPC block present"

wait_rpc() {
  local sec="${MN2_RPC_WAIT_SEC:-180}" i max h
  max=$((sec / 5))
  [[ "$max" -lt 6 ]] && max=6
  for ((i = 1; i <= max; i++)); do
    if ss -tln 2>/dev/null | grep -q ':9332'; then
      h="$($CLI getblockcount 2>/dev/null || echo -1)"
      if [[ "$h" =~ ^[0-9]+$ ]] && [[ "$h" -gt 0 ]]; then
        log "RPC ready height=$h (ss :9332 listening)"
        return 0
      fi
      log "wait $i/$max — :9332 up, getblockcount=$h (chain loading?)"
    else
      log "wait $i/$max — :9332 not listening yet"
    fi
    sleep 5
  done
  log "ERROR: RPC not ready after ${sec}s (check journalctl -u $UNIT)"
  return 1
}

if [[ "$RESTART_DAEMON" -eq 1 ]]; then
  log "Restarting $UNIT"
  systemctl restart "$UNIT"
  wait_rpc || exit 1
fi

log "Done — next: curl http://127.0.0.1:9332/ and restart uwsgi-vidgenerator"
