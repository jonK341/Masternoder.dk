#!/usr/bin/env bash
# Force app RPC back to primary (local wallet RPC from .env). Use when failover state stuck on standby.
set -euo pipefail
WEB="${WEB_ROOT:-/var/www/html}"
STATE="${WEB}/data/mn2_rpc_failover_state.json"
mkdir -p "$(dirname "$STATE")"
cat >"$STATE" <<'EOF'
{
  "active": "primary",
  "primary_fail_streak": 0,
  "standby_fail_streak": 0,
  "promoted_at": null,
  "promote_reason": null
}
EOF
echo "[mn2-failover-reset] wrote $STATE (active=primary)"
if [[ -f "${WEB}/.venv/bin/python" ]] || command -v python3 >/dev/null; then
  PY="${WEB}/.venv/bin/python"
  [[ -x "$PY" ]] || PY=python3
  cd "$WEB"
  set -a
  # shellcheck source=/dev/null
  [[ -f "${WEB}/.env" ]] && source "${WEB}/.env" 2>/dev/null || true
  set +a
  "$PY" -c "
from backend.services.mn2_rpc_failover import force_failback_primary
import json
print(json.dumps(force_failback_primary(), indent=2))
" 2>/dev/null || echo "(python failback skipped — state file reset is enough)"
fi
echo "Restart uWSGI: systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001"
