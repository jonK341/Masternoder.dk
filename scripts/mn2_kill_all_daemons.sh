#!/usr/bin/env bash
# Stop ALL masternoder2d processes quickly (by PID), clear datadir lock, restart systemd unit.
#
# Faster than mn2_repair_daemon.sh --stop-orphan when several duplicates fight over .lock.
# Does not use pkill -f — only pgrep -x / explicit PIDs.
#
# Usage (on server as root):
#   ./scripts/mn2_kill_all_daemons.sh
#   ./scripts/mn2_kill_all_daemons.sh --no-start          # kill only, do not systemctl start
#   ./scripts/mn2_kill_all_daemons.sh --wait-rpc 60       # poll getblockcount after start
#
# Env: MN2_DATADIR, MN2_UNIT, MN2_CLI

set -euo pipefail

DATADIR="${MN2_DATADIR:-/var/www/html/config}"
UNIT="${MN2_UNIT:-masternoder2d}"
LOCK="${DATADIR}/.lock"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
NO_START=0
WAIT_RPC=25

log() { echo "[mn2-kill-all] $*" >&2; }

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \?//'
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-start) NO_START=1 ;;
    --wait-rpc)
      shift
      WAIT_RPC="${1:-25}"
      ;;
    -h|--help) usage ;;
    *)
      log "unknown arg: $1"
      usage
      ;;
  esac
  shift
done

collect_pids() {
  pgrep -x masternoder2d 2>/dev/null | sort -u || true
}

kill_all_pids() {
  local pid sig label
  sig="$1"
  label="$2"
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    if kill "-${sig}" "$pid" 2>/dev/null; then
      log "${label} pid ${pid}"
    fi
  done < <(collect_pids)
}

wait_unit_stopped() {
  local i pid
  for i in $(seq 1 15); do
    pid="$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null || echo 0)"
    [[ -z "$pid" || "$pid" == "0" ]] && return 0
    sleep 1
  done
  log "WARN: ${UNIT} MainPID still ${pid} after stop wait"
}

log "stopping ${UNIT}"
systemctl stop "$UNIT" 2>/dev/null || true
wait_unit_stopped

log "SIGTERM all masternoder2d PIDs"
kill_all_pids TERM TERM
sleep 2

log "SIGKILL remaining PIDs"
kill_all_pids 9 KILL
sleep 1

if [[ -n "$(collect_pids)" ]]; then
  log "second KILL sweep"
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    kill -9 "$pid" 2>/dev/null || true
    log "KILL pid ${pid}"
  done < <(collect_pids)
  sleep 1
fi

remaining="$(collect_pids | tr '\n' ' ')"
if [[ -n "${remaining// /}" ]]; then
  log "ERROR: still running PIDs: ${remaining}"
  pgrep -af "[m]asternoder2d" >&2 || true
  exit 1
fi

if [[ -f "$LOCK" ]]; then
  log "removing lock ${LOCK}"
  rm -f "$LOCK"
fi

if [[ "$NO_START" -eq 1 ]]; then
  log "done (--no-start); start manually: systemctl start ${UNIT}"
  exit 0
fi

log "starting ${UNIT}"
systemctl start "$UNIT"

if [[ "$WAIT_RPC" -gt 0 ]] && [[ -x "$CLI" ]]; then
  log "waiting up to ${WAIT_RPC}s for RPC getblockcount"
  for _ in $(seq 1 "$WAIT_RPC"); do
    if out="$("$CLI" -datadir="$DATADIR" getblockcount 2>&1)" && [[ "$out" =~ ^[0-9]+$ ]]; then
      log "RPC ok height=${out}"
      exit 0
    fi
    sleep 1
  done
  log "WARN: RPC not ready after ${WAIT_RPC}s — check: journalctl -u ${UNIT} -n 40"
  exit 1
fi

log "done"
exit 0
