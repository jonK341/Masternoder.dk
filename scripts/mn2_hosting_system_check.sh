#!/usr/bin/env bash
# Requirements check for MN2 masternode hosting (registry, checkout, daemon, reconcile flag).
# Usage: cd /var/www/html && bash scripts/mn2_hosting_system_check.sh
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"
export PYTHONPATH="${WEB}${PYTHONPATH:+:$PYTHONPATH}"
[[ -f .env ]] && set -a && source .env && set +a

python3 <<'PY'
import json
from scripts.daemon_env import load_dotenv

load_dotenv()
from backend.services import mn2_masternode_service as mn

svc = mn.get_service_status(fresh=True)
snap = mn.rented_masternodes_snapshot()
out = {
    "requirements": {
        "service_enabled": bool(svc.get("enabled")),
        "auto_provision": bool(snap.get("auto_provision")),
        "daemon_healthy": bool(snap.get("daemon_healthy")),
        "multi_ping_capable": (svc.get("daemon") or {}).get("multi_ping_capable"),
        "multi_ping_enabled": (svc.get("daemon") or {}).get("multi_ping_enabled"),
        "checkout_open": bool(svc.get("checkout_open")),
        "reconcile_paid_orders": svc.get("reconcile_paid_orders"),
    },
    "capacity": {
        "slots_available": svc.get("slots_available"),
        "collateral_outputs_available": svc.get("collateral_outputs_available"),
        "hosted_count": svc.get("hosted_count"),
        "waiting_slots": svc.get("waiting_slots"),
        "registry_count": svc.get("registry_count"),
    },
    "orders": svc.get("paid_rental_stats") or {},
    "blockers": snap.get("blockers"),
    "checkout_closed_reason": svc.get("checkout_closed_reason"),
}
print(json.dumps(out, indent=2))
ok = (
    out["requirements"]["service_enabled"]
    and out["requirements"]["daemon_healthy"]
    and (out["requirements"]["checkout_open"] or out["capacity"]["collateral_outputs_available"] == 0)
)
raise SystemExit(0 if ok else 1)
PY
