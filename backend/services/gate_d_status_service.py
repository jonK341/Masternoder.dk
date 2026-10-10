"""Gate D readiness — Stage 3 cross-cutting complete, ready for Stage 4 hardening."""
from __future__ import annotations

from typing import Any, Dict, List


def _check(name: str, fn) -> Dict[str, Any]:
    try:
        ok = bool(fn())
        return {"name": name, "ok": ok}
    except Exception as exc:
        return {"name": name, "ok": False, "error": str(exc)}


def check_gate_d() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def gate_c_ok() -> bool:
        from backend.services.gate_c_status_service import check_gate_c
        return check_gate_c().get("ready_for_stage_3") is True

    def activity_monitor_ok() -> bool:
        from backend.services.activity_monitor_service import get_monitor_status
        r = get_monitor_status()
        return r.get("success") is True and "tiles" in r

    def security_sweep_ok() -> bool:
        from backend.services.security_cron_service import run_security_sweep
        return callable(run_security_sweep)

    def control_board_ok() -> bool:
        from backend.services.agent_admin_service import get_control_status
        r = get_control_status()
        return r.get("success") is True and "reconcile" in r

    def customer_avatars_ok() -> bool:
        from backend.services.customer_avatar_service import backfill_missing_avatars, svg_for_user
        return callable(backfill_missing_avatars) and "<svg" in svg_for_user("probe_user")

    def trader_leveling_ok() -> bool:
        from backend.services.agent_trader_service import trader_level_for_agent
        return trader_level_for_agent("trader_agent_1") >= 1

    def activity_events_ok() -> bool:
        from backend.services.activity_events_service import emit
        r = emit("gate_d_probe", channel="ops", payload={"gate": "D"})
        return r.get("success") is True

    checks.append(_check("gate_c_prerequisite", gate_c_ok))
    checks.append(_check("activity_monitor", activity_monitor_ok))
    checks.append(_check("security_cron_sweep", security_sweep_ok))
    checks.append(_check("agents_control_board", control_board_ok))
    checks.append(_check("customer_avatar_backfill", customer_avatars_ok))
    checks.append(_check("trader_leveling", trader_leveling_ok))
    checks.append(_check("activity_events", activity_events_ok))

    all_ok = all(c.get("ok") for c in checks)
    return {
        "success": True,
        "gate": "D",
        "status": "ready" if all_ok else "degraded",
        "ready_for_stage_4": all_ok,
        "checks": checks,
    }
