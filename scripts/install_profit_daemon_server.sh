#!/usr/bin/env bash
# Install systemd unit for 24/7 profit daemon on masternoder.dk.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_SRC="$ROOT/systemd/masternoder-profit-daemon.service"
UNIT_DST="/etc/systemd/system/masternoder-profit-daemon.service"

chmod +x "$ROOT/scripts/run_profit_daemon_server.sh"
mkdir -p "$ROOT/logs"
chmod 755 "$ROOT/logs"
touch "$ROOT/logs/daemon_all_profit_heartbeat.json"
chmod 644 "$ROOT/logs/daemon_all_profit_heartbeat.json" 2>/dev/null || true

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "Missing $UNIT_SRC"
  exit 1
fi

cp "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
systemctl enable masternoder-profit-daemon.service
systemctl restart masternoder-profit-daemon.service
sleep 3
systemctl --no-pager status masternoder-profit-daemon.service || true
echo "Profit daemon installed. Logs: $ROOT/logs/profit_daemon_stdout.log"
