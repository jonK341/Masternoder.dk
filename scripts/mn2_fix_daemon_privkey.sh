#!/usr/bin/env bash
# Fix masternoder2.conf masternodeprivkey to match primary_ping_alias in masternode.conf.
# Must run as root on the production server (www-data cannot write masternoder2.conf).
#
# Usage:
#   sudo bash /var/www/html/scripts/mn2_fix_daemon_privkey.sh
#   sudo bash /var/www/html/scripts/mn2_fix_daemon_privkey.sh --restart-only
#   PRIMARY=platformmn2 sudo bash /var/www/html/scripts/mn2_fix_daemon_privkey.sh
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
CONFIG="${MN2_DATADIR:-$WEB/config}"
MN_CONF="$CONFIG/masternode.conf"
DCONF="$CONFIG/masternoder2.conf"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli -datadir=$CONFIG}"
UNIT="${MN2_DAEMON_UNIT:-masternoder2d}"
PRIMARY="${PRIMARY:-platformmn2}"
RESTART_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --restart-only) RESTART_ONLY=1 ;;
    --primary=*) PRIMARY="${arg#*=}" ;;
  esac
done

log() { echo "[fix-privkey] $*"; }

read_primary_privkey() {
  local line parts
  while IFS= read -r line; do
    line="${line%%#*}"
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" ]] && continue
    read -r -a parts <<< "$line"
    if [[ "${parts[0]}" == "$PRIMARY" && ${#parts[@]} -eq 5 && "${parts[1]}" == *:* ]]; then
      echo "${parts[2]}"
      return 0
    fi
  done < "$MN_CONF"
  return 1
}

read_daemon_privkey() {
  grep '^masternodeprivkey=' "$DCONF" 2>/dev/null | cut -d= -f2- | tail -1 || true
}

distinct_privkey_count() {
  grep '^masternodeprivkey=' "$DCONF" 2>/dev/null | cut -d= -f2- | sort -u | wc -l | tr -d ' '
}

needs_masternode_block_normalize() {
  local pk_count distinct
  pk_count=$(grep -c '^masternodeprivkey=' "$DCONF" 2>/dev/null || echo 0)
  distinct=$(distinct_privkey_count)
  if [[ "$pk_count" -gt 1 ]]; then
    return 0
  fi
  if [[ "$distinct" -gt 1 ]]; then
    log "ERROR: conflicting masternodeprivkey values in $DCONF"
    exit 1
  fi
  if [[ "$(grep -c '^masternode=1' "$DCONF" 2>/dev/null || echo 0)" -gt 1 ]]; then
    return 0
  fi
  if [[ "$(grep -c '^masternodeaddr=' "$DCONF" 2>/dev/null || echo 0)" -gt 1 ]]; then
    return 0
  fi
  return 1
}

write_masternode_block() {
  local privkey="$1"
  local port extip pingaddr
  port="$(grep '^port=' "$DCONF" 2>/dev/null | tail -1 | cut -d= -f2- || echo 17646)"
  extip="$(grep '^externalip=' "$DCONF" 2>/dev/null | tail -1 | cut -d= -f2- || echo 140.82.39.124)"
  pingaddr="$(grep '^masternodeaddr=' "$DCONF" 2>/dev/null | tail -1 | cut -d= -f2- || echo "127.0.0.1:${port}")"
  port="${port:-17646}"
  extip="${extip:-140.82.39.124}"
  pingaddr="${pingaddr:-127.0.0.1:${port}}"
  {
    grep -vE '^(listen=|port=|externalip=|masternode=1|masternodeprivkey=|masternodeaddr=)' "$DCONF" || true
    echo "listen=1"
    echo "port=${port}"
    echo "externalip=${extip}"
    echo "masternode=1"
    echo "masternodeprivkey=${privkey}"
    echo "masternodeaddr=${pingaddr}"
  } > "$DCONF"
  chown root:www-data "$DCONF"
  chmod 640 "$DCONF"
  CONFIG_DIR=$(dirname "$DCONF")
  chown root:www-data "$CONFIG_DIR"
  chmod 775 "$CONFIG_DIR"
}

wait_rpc() {
  local i max sec="${MN2_RPC_WAIT_SEC:-180}"
  max=$((sec / 5))
  [[ "$max" -lt 6 ]] && max=6
  for ((i = 1; i <= max; i++)); do
    if systemctl is-active --quiet "$UNIT" && $CLI getblockcount 2>/dev/null | grep -qE '^[0-9]+$'; then
      log "RPC ready height=$($CLI getblockcount 2>/dev/null)"
      return 0
    fi
    sleep 5
  done
  log "ERROR: RPC not ready after daemon restart (${sec}s)"
  return 1
}

if [[ ! -f "$MN_CONF" ]]; then
  log "ERROR: missing $MN_CONF"
  exit 1
fi
if [[ ! -f "$DCONF" ]]; then
  log "ERROR: missing $DCONF"
  exit 1
fi

WANT="$(read_primary_privkey)" || {
  log "ERROR: no privkey for alias $PRIMARY in $MN_CONF"
  exit 1
}
HAVE="$(read_daemon_privkey)"

if [[ "$RESTART_ONLY" -eq 1 ]]; then
  log "Restart-only mode"
  systemctl restart "$UNIT"
  wait_rpc || exit 1
elif [[ "$HAVE" == "$WANT" ]] && ! needs_masternode_block_normalize; then
  log "OK masternodeprivkey already matches $PRIMARY (${WANT:0:8}…)"
else
  if [[ "$HAVE" != "$WANT" ]]; then
    log "Fixing privkey: have ${HAVE:0:8}… want ${WANT:0:8}… ($PRIMARY)"
  else
    log "Deduping masternode block lines in $DCONF (duplicate privkey/masternode=1 detected)"
  fi
  write_masternode_block "$WANT"
  log "Updated $DCONF"
  systemctl restart "$UNIT"
  wait_rpc || exit 1
fi

log "Starting primary alias $PRIMARY (alias then local)"
$CLI startmasternode alias false "$PRIMARY" 2>/dev/null || true
$CLI startmasternode local false 2>/dev/null || true

log "Done — verify with: grep masternodeprivkey= $DCONF"
