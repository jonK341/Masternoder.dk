#!/usr/bin/env bash
# Stop every script that hammers masternoder2d RPC (fixes HTTP 500 work queue depth).
#
# Usage: bash /var/www/html/scripts/mn2_stop_fleet_ops.sh
# Keeps the caller alive: MN2_STOP_FLEET_KEEP_PIDS="$$" bash scripts/mn2_stop_fleet_ops.sh
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
log() { echo "[stop-fleet-ops] $*" >&2; }

_should_skip_pid() {
  local pid="$1"
  [[ -z "$pid" || "$pid" == "$$" ]] && return 0
  # Do not kill the script that invoked this helper (e.g. activate-all / fleet recovery).
  [[ "$pid" == "$PPID" ]] && return 0
  local extra
  for extra in ${MN2_STOP_FLEET_KEEP_PIDS:-}; do
    [[ "$pid" == "$extra" ]] && return 0
  done
  return 1
}

patterns=(
  mn2_activate_all_rented
  mn2_fleet_full_recovery
  mn2_bring_rented_online
  mn2_start_masternode
  mn2_recover_pending
  mn2_fleet_audit
  mn2_masternode_start_fleet
)

for pass in 1 2; do
  for pat in "${patterns[@]}"; do
    while read -r pid; do
      _should_skip_pid "$pid" && continue
      log "kill pid $pid ($pat)"
      kill -TERM "$pid" 2>/dev/null || true
    done < <(pgrep -f "$pat" 2>/dev/null || true)
  done
  sleep 2
  for pat in "${patterns[@]}"; do
    while read -r pid; do
      _should_skip_pid "$pid" && continue
      kill -9 "$pid" 2>/dev/null || true
    done < <(pgrep -f "$pat" 2>/dev/null || true)
  done
done

parent_cmd=$(ps -o args= -p "${PPID:-0}" 2>/dev/null || true)
if [[ "$parent_cmd" != *mn2_activate_all_rented* ]]; then
  rm -f "$WEB/data/mn2_activate_all.lock" 2>/dev/null || true
fi

remaining=$(pgrep -af 'mn2_activate_all|mn2_fleet_full|mn2_bring_rented|mn2_start_masternode' 2>/dev/null || true)
if [[ -n "${remaining:-}" ]]; then
  log "remaining processes:"
  echo "$remaining" >&2
else
  log "no fleet ops processes left"
fi
