#!/usr/bin/env bash
# One RPC call: startmasternode all false (multi-ping). No provisioning drain.
# Can take 5-30+ minutes with ~90+ masternode.conf lines — do not Ctrl+C.
#
# Usage:
#   cd /var/www/html && bash scripts/mn2_fleet_ping_only.sh
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
DATADIR="${MN2_DATADIR:-$WEB/config}"

if [[ -f "$WEB/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$WEB/.env"
  set +a
fi

echo "[fleet-ping] CLI getblockcount…" >&2
if ! h=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1) || [[ ! "$h" =~ ^[0-9]+$ ]]; then
  echo "[fleet-ping] ERROR: RPC not ready: ${h:0:120}" >&2
  echo "[fleet-ping] Run: bash scripts/mn2_rpc_quiet_recovery.sh" >&2
  exit 1
fi
echo "[fleet-ping] height=$h — running startmasternode all false (long-running)…" >&2

if command -v timeout >/dev/null 2>&1; then
  timeout "${MN2_RPC_STARTMN_ALL_TIMEOUT:-1800}" "$CLI" -datadir="$DATADIR" startmasternode all false
else
  "$CLI" -datadir="$DATADIR" startmasternode all false
fi

echo "[fleet-ping] done" >&2
