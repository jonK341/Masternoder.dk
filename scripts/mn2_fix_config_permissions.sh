#!/usr/bin/env bash
# Ensure MN2 config files are readable by www-data (Flask/uwsgi) and writable where needed.
# masternoder2.conf: root-owned ping block — www-data must read (640), root rewrites via fix-privkey.
# masternode.conf: www-data append on provision (664).
# config/: www-data must create masternode.conf.tmp.* (atomic write) — root:www-data 775.
#
# Usage (on server as root):
#   sudo bash /var/www/html/scripts/mn2_fix_config_permissions.sh
#   sudo bash /var/www/html/scripts/mn2_fix_config_permissions.sh --verify
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
CONFIG="${MN2_DATADIR:-$WEB/config}"
DCONF="$CONFIG/masternoder2.conf"
MN_CONF="$CONFIG/masternode.conf"
VERIFY=0

for arg in "$@"; do
  case "$arg" in
    --verify) VERIFY=1 ;;
  esac
done

log() { echo "[fix-config-perms] $*"; }

apply_perms() {
  if [[ ! -d "$CONFIG" ]]; then
    log "ERROR: missing config dir $CONFIG"
    return 1
  fi

  chown root:www-data "$CONFIG"
  chmod 775 "$CONFIG"
  log "OK $CONFIG -> root:www-data 775 (www-data can create .tmp files)"

  if [[ -f "$DCONF" ]]; then
    chown root:www-data "$DCONF"
    chmod 640 "$DCONF"
    log "OK $DCONF -> root:www-data 640"
  else
    log "WARN: missing $DCONF (skip)"
  fi

  if [[ -f "$MN_CONF" ]]; then
    chown www-data:www-data "$MN_CONF"
    chmod 664 "$MN_CONF"
    log "OK $MN_CONF -> www-data:www-data 664"
  else
    log "WARN: missing $MN_CONF (skip)"
  fi

  return 0
}

verify_perms() {
  local ok=0
  if [[ -d "$CONFIG" ]] && [[ -r "$CONFIG" && -x "$CONFIG" ]]; then
    log "OK config dir traversable: $CONFIG"
  else
    log "FAIL config dir not traversable: $CONFIG"
    ok=1
  fi
  if [[ -d "$CONFIG" ]]; then
    if sudo -u www-data test -w "$CONFIG" 2>/dev/null; then
      log "OK www-data can create files in $CONFIG"
    else
      log "FAIL www-data cannot write in $CONFIG (need root:www-data 775 for masternode.conf.tmp)"
      ok=1
    fi
  fi
  if [[ -f "$DCONF" ]]; then
    if sudo -u www-data test -r "$DCONF" 2>/dev/null; then
      log "OK www-data can read $DCONF"
    else
      log "FAIL www-data cannot read $DCONF"
      ok=1
    fi
  fi
  if [[ -f "$MN_CONF" ]]; then
    if sudo -u www-data test -r "$MN_CONF" 2>/dev/null; then
      log "OK www-data can read $MN_CONF"
    else
      log "FAIL www-data cannot read $MN_CONF"
      ok=1
    fi
    if sudo -u www-data test -w "$MN_CONF" 2>/dev/null; then
      log "OK www-data can write $MN_CONF"
    else
      log "FAIL www-data cannot write $MN_CONF"
      ok=1
    fi
  fi
  return "$ok"
}

if [[ "$VERIFY" -eq 1 ]]; then
  verify_perms
  exit $?
fi

apply_perms
verify_perms || true
log "Done"
