"""Security cron sweep — conservation, drift, deposits, treasury reconcile (Stage 3)."""
from __future__ import annotations

from typing import Any, Dict


def run_security_sweep(*, drift_limit: int = 100) -> Dict[str, Any]:
    """Run all security sweep checks; safe to call from cron or HTTP."""
    results: Dict[str, Any] = {}

    try:
        from backend.services.mn2_conservation_gate import conservation_gate
        results["conservation"] = conservation_gate()
    except Exception as exc:
        results["conservation"] = {"error": str(exc)}

    try:
        from backend.services.points_drift_service import scan_all
        results["points_drift"] = scan_all(limit=max(1, min(int(drift_limit or 100), 500)))
    except Exception as exc:
        results["points_drift"] = {"error": str(exc)}

    try:
        from backend.services.mn2_deposit_scanner import run_scanner
        results["deposit_scanner"] = run_scanner()
    except Exception as exc:
        results["deposit_scanner"] = {"error": str(exc)}

    try:
        from backend.services.agent_admin_service import reconcile_treasury_pool
        results["treasury_reconcile"] = reconcile_treasury_pool()
    except Exception as exc:
        results["treasury_reconcile"] = {"error": str(exc)}

    try:
        from backend.services.agent_kill_switch import get_status
        results["agent_kill_switch"] = get_status()
    except Exception as exc:
        results["agent_kill_switch"] = {"error": str(exc)}

    ok = True
    for key, val in results.items():
        if isinstance(val, dict) and val.get("error") and key == "conservation":
            ok = False
        if key == "treasury_reconcile" and isinstance(val, dict) and val.get("ok") is False:
            ok = False

    return {"success": True, "ok": ok, "results": results}
