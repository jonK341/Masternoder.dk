#!/usr/bin/env bash
# Retry auto-provision for paid masternode slots (collateral confirming / start pending).
set -euo pipefail
cd /var/www/html
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/mn2_read_ops_secret.sh"
curl -s -X POST -H "X-Ops-Secret: ${MN2_OPS_SECRET}" \
  "http://127.0.0.1:5000/api/mn2/masternode/provision-pending?limit=20"
