#!/usr/bin/env bash
# Print ops secret length and test provision/collateral without HTTP (uses .env + Python RPC).
set -euo pipefail
cd "${WEB_ROOT:-/var/www/html}"
set -a
# shellcheck source=/dev/null
source .env
set +a

echo "== MN2 RPC (Python, same as ops scripts) =="
python3 -c "
from backend.services.mn2_rpc_client import health_check
import json
print(json.dumps(health_check(), indent=2))
"

echo ""
echo "== Collateral pool (free ~5000 MN2 UTXOs) =="
python3 -c "
from backend.services.mn2_masternode_service import list_collateral_outputs
import json
print(json.dumps(list_collateral_outputs(), indent=2)[:4000])
"

echo ""
echo "== Pending snapshot (counts only) =="
python3 -c "
from backend.services.mn2_masternode_service import rented_masternodes_snapshot
import json
s=rented_masternodes_snapshot()
print('daemon_healthy', s.get('daemon_healthy'))
print('blockers', s.get('blockers'))
pend=s.get('pending') or []
print('pending_count', len(pend))
print('no_collateral', sum(1 for p in pend if not p.get('has_collateral')))
print('active_count', s.get('active_count'))
"

echo ""
echo "== Ops secret (for curl) =="
source cron/mn2_read_ops_secret.sh
SECRET=$(mn2_read_ops_secret || true)
echo "MN2_OPS_SECRET length: ${#SECRET}"
if [ "${#SECRET}" -eq 0 ]; then
  echo "FIX: set MN2_OPS_SECRET= in .env"
  exit 1
fi

echo ""
echo "Run small provision batch:"
echo "  set -a && source .env && set +a"
echo "  python3 scripts/mn2_bring_rented_online.py --provision-only --limit 10"
