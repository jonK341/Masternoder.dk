#!/bin/bash
# Run on production as root (or deploy user). Joins trader agents to MN2 staking pool.
set -euo pipefail
WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"

echo "== trader-staking join-pool =="

# Prefer direct service call (no HTTP ops secret needed)
if [[ -x ./venv/bin/python ]]; then
  ./venv/bin/python <<'PY'
import json
import sys
sys.path.insert(0, ".")
from backend.services.agent_trader_staking_service import join_trader_agents_to_pool
out = join_trader_agents_to_pool(dry_run=False)
print(json.dumps(out, indent=2))
sys.exit(0 if out.get("success") else 1)
PY
  exit $?
fi

ENV="$WEB/.env"
SECRET=""
for key in MN2_OPS_SECRET MN2_SCAN_SECRET DISCORD_OPS_SECRET ADMIN_OPS_SECRET; do
  line=$(grep -E "^${key}=" "$ENV" 2>/dev/null | head -1 || true)
  if [[ -n "$line" ]]; then
    SECRET=$(echo "$line" | cut -d= -f2- | tr -d '\r"')
    break
  fi
done
if [[ -z "$SECRET" ]]; then
  echo "No ops secret in $ENV and venv python missing" >&2
  exit 1
fi
curl -sS -X POST \
  -H "X-Ops-Secret: $SECRET" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "http://127.0.0.1:5000/api/agents/trader-staking/join-pool"
echo
