#!/usr/bin/env bash
# Diagnose and repair masternoder2d lock / duplicate-daemon conflicts.
#
# Typical failure: a manual `masternoder2d -reindex -daemon=1` orphan holds
# /var/www/html/config while systemd keeps restarting a second instance.
#
# Usage:
#   ./scripts/mn2_repair_daemon.sh              # status only
#   ./scripts/mn2_repair_daemon.sh --stop-orphan # kill non-systemd daemon, clear lock, start unit
#   ./scripts/mn2_repair_daemon.sh --keep-orphan # stop/disable systemd; leave manual daemon running
#
# Env: MN2_DATADIR (default /var/www/html/config), MN2_UNIT (default masternoder2d)

set -euo pipefail

DATADIR="${MN2_DATADIR:-/var/www/html/config}"
UNIT="${MN2_UNIT:-masternoder2d}"
LOCK="${DATADIR}/.lock"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
MODE="${1:-status}"

log() { echo "[mn2-repair] $*" >&2; }

list_daemons() {
  pgrep -af "[m]asternoder2d" || true
}

systemd_main_pid() {
  systemctl show -p MainPID --value "$UNIT" 2>/dev/null || echo "0"
}

print_status() {
  echo "== $UNIT =="
  systemctl is-active "$UNIT" 2>/dev/null || echo inactive
  echo "systemd MainPID: $(systemd_main_pid)"
  echo
  echo "== masternoder2d processes =="
  list_daemons
  echo
  echo "== ports =="
  ss -tlnp 2>/dev/null | grep -E '9332|17646' || echo "(none listening)"
  echo
  echo "== lock =="
  ls -la "$LOCK" 2>/dev/null || echo "(no lock file)"
  echo
  if [[ -x "$CLI" ]]; then
    echo "== RPC (via existing daemon) =="
    "$CLI" -datadir="$DATADIR" getblockchaininfo 2>/dev/null | grep -E '"blocks"|"headers"|"verificationprogress"|"initialblockdownload"' || \
      echo "(RPC not responding — daemon may be busy reindexing or auth/config issue)"
  fi
}

stop_orphan_and_start_unit() {
  log "stopping $UNIT"
  systemctl stop "$UNIT" 2>/dev/null || true
  sleep 3

  local pid unit_pid
  unit_pid="$(systemd_main_pid)"
  while read -r line; do
    [[ -z "$line" ]] && continue
    pid="${line%% *}"
    if [[ "$pid" == "$unit_pid" && "$unit_pid" != "0" ]]; then
      continue
    fi
    if [[ "$line" == *"masternoder2d"* ]]; then
      log "stopping orphan pid $pid: ${line#* }"
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done < <(pgrep -af "[m]asternoder2d" || true)

  sleep 8
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    log "force-killing pid $pid"
    kill -9 "$pid" 2>/dev/null || true
  done < <(pgrep -x masternoder2d 2>/dev/null || true)

  sleep 2
  rm -f "$LOCK"
  log "starting $UNIT"
  systemctl start "$UNIT"
  sleep 5
  print_status
}

keep_orphan_disable_unit() {
  log "stopping and disabling $UNIT (manual daemon keeps running)"
  systemctl stop "$UNIT" 2>/dev/null || true
  systemctl disable "$UNIT" 2>/dev/null || true
  print_status
  log "Re-enable when the manual daemon exits: systemctl enable --now $UNIT"
}

case "$MODE" in
  status|"")
    print_status
    orphans="$(pgrep -x masternoder2d 2>/dev/null | wc -l | tr -d ' ')"
    unit_active="$(systemctl is-active "$UNIT" 2>/dev/null || true)"
    if [[ "$orphans" -gt 1 || ( "$orphans" -eq 1 && "$unit_active" == "active" ) ]]; then
      log "duplicate or conflicting daemon detected"
      log "  --stop-orphan   kill manual daemon, start systemd unit"
      log "  --keep-orphan   disable systemd, keep manual -reindex daemon"
      exit 1
    fi
    ;;
  --stop-orphan)
    stop_orphan_and_start_unit
    ;;
  --keep-orphan)
    keep_orphan_disable_unit
    ;;
  *)
    log "unknown mode: $MODE (use status, --stop-orphan, or --keep-orphan)"
    exit 2
    ;;
esac
