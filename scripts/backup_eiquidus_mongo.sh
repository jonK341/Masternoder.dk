#!/bin/bash
# Backup eiquidus MongoDB before reindex (P4 #181).
# Usage: sudo ./scripts/backup_eiquidus_mongo.sh [output_dir]
set -euo pipefail

OUT_DIR="${1:-/var/backups/eiquidus}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${OUT_DIR}/eiquidus-mongo-${STAMP}"

MONGO_DB="${EQUIDUS_MONGO_DB:-iquidus}"
MONGO_HOST="${EQUIDUS_MONGO_HOST:-127.0.0.1}"
MONGO_PORT="${EQUIDUS_MONGO_PORT:-27017}"

mkdir -p "$OUT_DIR"
echo "Backing up MongoDB ${MONGO_DB}@${MONGO_HOST}:${MONGO_PORT} -> ${DEST}"

if command -v mongodump >/dev/null 2>&1; then
  mongodump --host "${MONGO_HOST}" --port "${MONGO_PORT}" --db "${MONGO_DB}" --out "${DEST}"
elif command -v docker >/dev/null 2>&1; then
  docker exec eiquidus-mongo mongodump --db "${MONGO_DB}" --out "/backup/${STAMP}" || {
    echo "Set EQUIDUS_MONGO_CONTAINER or install mongodump" >&2
    exit 1
  }
else
  echo "mongodump not found — install mongodb-database-tools" >&2
  exit 1
fi

tar -czf "${DEST}.tar.gz" -C "$(dirname "$DEST")" "$(basename "$DEST")"
rm -rf "$DEST"
echo "OK: ${DEST}.tar.gz"
