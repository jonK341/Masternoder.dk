#!/usr/bin/env bash
# Root cron: restart masternoder2d when RPC work queue is saturated, then provision pending slots.
set -euo pipefail
cd /var/www/html
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATADIR="${MN2_DATADIR:-/var/www/html/config}"
CLI="${MN2_CLI:-/opt/masternoder2d/masternoder2-cli}"
UNIT="${MN2_DAEMON_UNIT:-masternoder2d}"

probe_rpc() {
  local out
  out=$("$CLI" -datadir="$DATADIR" getblockcount 2>&1) || true
  if echo "$out" | grep -qiE 'work queue|loading block index|verifying'; then
    return 1
  fi
  echo "$out" | grep -qE '^[0-9]+$'
}

if probe_rpc; then
  exit 0
fi

echo "[mn2-masternode-recover] RPC unhealthy — restarting ${UNIT}" >&2
systemctl restart "$UNIT"
sleep 25
for _ in $(seq 1 24); do
  if probe_rpc; then
    break
  fi
  sleep 5
done

if [ -f "${SCRIPT_DIR}/mn2_read_ops_secret.sh" ]; then
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/mn2_read_ops_secret.sh"
  curl -s -X POST -H "X-Ops-Secret: ${MN2_OPS_SECRET}" \
    "http://127.0.0.1:5000/api/mn2/masternode/recover?limit=50&restart_daemon=0" >/dev/null || true
fi
