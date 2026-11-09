#!/usr/bin/env bash
# Set MN2_RPC_MAX_RETRIES=1 in production .env and reload uwsgi.
#
# Usage (on server as root):
#   sudo bash /var/www/html/scripts/mn2_patch_rpc_retries.sh
# Or one-liner:
#   sudo bash -c 'ENV=/var/www/html/.env; grep -q "^MN2_RPC_MAX_RETRIES=" "$ENV" && sed -i "s/^MN2_RPC_MAX_RETRIES=.*/MN2_RPC_MAX_RETRIES=1/" "$ENV" || echo "MN2_RPC_MAX_RETRIES=1" >> "$ENV"; systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001'
set -euo pipefail

ENV="${ENV_FILE:-/var/www/html/.env}"
KEY=MN2_RPC_MAX_RETRIES
VAL=1

if [[ ! -f "$ENV" ]]; then
  echo "[patch-rpc-retries] ERROR: missing $ENV" >&2
  exit 1
fi

if grep -q "^${KEY}=" "$ENV"; then
  sed -i "s/^${KEY}=.*/${KEY}=${VAL}/" "$ENV"
  echo "[patch-rpc-retries] updated ${KEY}=${VAL} in $ENV"
else
  echo "${KEY}=${VAL}" >> "$ENV"
  echo "[patch-rpc-retries] appended ${KEY}=${VAL} to $ENV"
fi

systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
echo "[patch-rpc-retries] restarted uwsgi-vidgenerator + uwsgi-vidgenerator-5001"
