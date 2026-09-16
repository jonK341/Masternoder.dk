#!/usr/bin/env bash
# Install and enable the exchange master daemon as a systemd service.
# Run on the production server: sudo bash scripts/install_exchange_daemon.sh  # pragma: allowlist secret
set -euo pipefail

UNIT_NAME="masternoder-exchange"
UNIT_FILE="systemd/exchange_master_daemon.service"
DEST="/etc/systemd/system/${UNIT_NAME}.service"
LOG_DIR="/var/log/masternoder"

echo "[exchange-daemon] Installing ${UNIT_NAME}.service ..."

if [[ ! -f "$UNIT_FILE" ]]; then
  echo "ERROR: ${UNIT_FILE} not found. Run from repo root." >&2
  exit 1
fi

# Create log directory
mkdir -p "$LOG_DIR"
chown www-data:www-data "$LOG_DIR"

# Copy unit file
cp "$UNIT_FILE" "$DEST"
chmod 644 "$DEST"

# Enable and (re)start
systemctl daemon-reload
systemctl enable "${UNIT_NAME}.service"
systemctl restart "${UNIT_NAME}.service"

echo "[exchange-daemon] Status:"
systemctl status "${UNIT_NAME}.service" --no-pager -l || true

echo ""
echo "[exchange-daemon] Done. Tail logs:"
echo "  sudo journalctl -u ${UNIT_NAME} -f"
echo "  tail -f ${LOG_DIR}/exchange_daemon.log"
