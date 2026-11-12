#!/usr/bin/env bash
# Run MasterNoder2 daemon with -datadir pointing at the deployed project config
#
# Windows: do not use PowerShell for chmod/export ./ — use Git Bash, WSL, or:
#   powershell -File scripts/run_masternoder2d.ps1
# Production daemon belongs on Linux: ssh to server, then bash this script.
# (reads /var/www/html/config/masternoder2.conf — same rpcuser/rpcpassword as app .env).
#
# On the server (after config is deployed):
#   chmod +x /var/www/html/scripts/run_masternoder2d.sh
#   # If binary is not in PATH, set full path:
#   export MN2_BINARY=/opt/masternoder2d/masternoder2d
#   ./scripts/run_masternoder2d.sh
#
# Background:
#   nohup ./scripts/run_masternoder2d.sh >> /var/log/masternoder2d.log 2>&1 &
#
# systemd: see systemd/masternoder2d.service.example

set -euo pipefail

DATADIR="${MN2_DATADIR:-/var/www/html/config}"
BIN="${MN2_BINARY:-}"

if [[ -z "$BIN" ]]; then
  if command -v masternoder2d &>/dev/null; then
    BIN="$(command -v masternoder2d)"
  elif [[ -x /opt/masternoder2d/masternoder2d ]]; then
    BIN=/opt/masternoder2d/masternoder2d
  elif [[ -x /opt/masternoder2d/masternoder2d/masternoder2d ]]; then
    BIN=/opt/masternoder2d/masternoder2d/masternoder2d
  elif [[ -x /usr/local/bin/masternoder2d ]]; then
    BIN=/usr/local/bin/masternoder2d
  else
    echo "masternoder2d not found. Install the binary or set MN2_BINARY to its full path." >&2
    exit 1
  fi
fi

if [[ ! -d "$DATADIR" ]]; then
  echo "ERROR: datadir does not exist: $DATADIR (set MN2_DATADIR if different)" >&2
  exit 1
fi

if [[ ! -f "$DATADIR/masternoder2.conf" ]]; then
  echo "WARNING: $DATADIR/masternoder2.conf missing — copy from config/masternoder2.conf.example and set rpcpassword." >&2
fi

echo "exec: $BIN -datadir=$DATADIR" >&2
exec "$BIN" -datadir="$DATADIR" "$@"
