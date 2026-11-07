#!/usr/bin/env bash
# Install MongoDB systemd drop-in for kernel 6.19–7.0.13 (MongoDB 8.0 startup guard).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/systemd/mongod-glibc-rseq.conf.example"
DEST_DIR="/etc/systemd/system/mongod.service.d"
DEST="${DEST_DIR}/glibc-rseq.conf"

if [[ ! -f "$SRC" ]]; then
  echo "Missing $SRC" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
cp "$SRC" "$DEST"
chmod 644 "$DEST"
systemctl daemon-reload

if systemctl list-unit-files mongod.service &>/dev/null || systemctl cat mongod.service &>/dev/null; then
  systemctl enable mongod 2>/dev/null || true
  systemctl restart mongod
  sleep 2
  systemctl is-active mongod
  if command -v mongosh &>/dev/null; then
    mongosh --quiet --eval 'db.adminCommand({ping:1})'
  fi
else
  echo "mongod.service not found — drop-in installed; start mongod after package install."
fi

echo "Installed $DEST"
