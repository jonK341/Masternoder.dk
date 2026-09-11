#!/usr/bin/env bash
# Remove a stale MasterNoder2 datadir lock when no daemon process is running.
# Safe to run from systemd ExecStartPre or manually before starting masternoder2d.
#
# Usage:
#   MN2_DATADIR=/var/www/html/config ./scripts/mn2_clear_daemon_lock.sh
#   systemctl stop masternoder2d && ./scripts/mn2_clear_daemon_lock.sh && systemctl start masternoder2d
#
# Exit 0: lock cleared or not needed. Exit 1: a live masternoder2d holds the datadir.

set -euo pipefail

DATADIR="${MN2_DATADIR:-/var/www/html/config}"
LOCK="${DATADIR}/.lock"

log() { echo "[mn2-clear-lock] $*" >&2; }

if [[ ! -d "$DATADIR" ]]; then
  log "datadir missing: $DATADIR"
  exit 1
fi

if pgrep -x masternoder2d >/dev/null 2>&1; then
  log "masternoder2d is running — not removing $LOCK"
  pgrep -af "[m]asternoder2d" >&2 || true
  log "If this is a manual -reindex -daemon=1 orphan, run: ./scripts/mn2_repair_daemon.sh --stop-orphan"
  log "Or keep it and disable systemd: ./scripts/mn2_repair_daemon.sh --keep-orphan"
  exit 1
fi

# Secondary check: any process with -datadir= pointing at this path
if pgrep -af "[m]asternoder2d.*-datadir=${DATADIR}" >/dev/null 2>&1; then
  log "masternoder2d with -datadir=$DATADIR is running — not removing $LOCK"
  pgrep -af "[m]asternoder2d" >&2 || true
  exit 1
fi

if [[ -f "$LOCK" ]]; then
  log "removing stale lock: $LOCK"
  rm -f "$LOCK"
else
  log "no lock file at $LOCK"
fi

exit 0
