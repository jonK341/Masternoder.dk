#!/usr/bin/env bash
# Retry auto-provision for paid masternode slots + keep masternode ping loop (activetime).
set -euo pipefail
cd /var/www/html
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Ensure www-data can append masternode.conf before provision (privkey rewrites may reset perms).
if [ -f scripts/mn2_fix_config_permissions.sh ]; then
  bash scripts/mn2_fix_config_permissions.sh 2>/dev/null || true
fi
# Network registration: startmasternode alone leaves conf as MISSING until broadcast is relayed.
if [ -f scripts/mn2_relay_missing_masternodes.py ]; then
  PYTHONPATH=/var/www/html python3 scripts/mn2_relay_missing_masternodes.py --limit 80 || true
fi
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/mn2_read_ops_secret.sh"
curl -s -X POST -H "X-Ops-Secret: ${MN2_OPS_SECRET}" \
  "http://127.0.0.1:5000/api/mn2/masternode/provision-pending?limit=50&skip_ping=0"
