"""Scan and activate trading agents that have never run or are gated off."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def scan_dormant_agents() -> Dict[str, Any]:
    from backend.services.trading_bots_control_service import _load_controls, list_bots

    controls = _load_controls()
    bots = list_bots(light=True)
    dormant: List[Dict[str, Any]] = []

    for b in bots:
        reasons: List[str] = []
        if controls.get("kill_switch"):
            reasons.append("kill_switch")
        if not b.get("enabled"):
            reasons.append("disabled")
        if int(b.get("trade_count") or 0) == 0:
            reasons.append("zero_trades")
        if b.get("fleet") and not b.get("last_run_at"):
            reasons.append("never_ran")
        if reasons:
            dormant.append({
                "id": b.get("id"),
                "name": b.get("name"),
                "kind": b.get("kind"),
                "supervisor": b.get("supervisor"),
                "enabled": b.get("enabled"),
                "trade_count": b.get("trade_count"),
                "last_run_at": b.get("last_run_at"),
                "reasons": reasons,
            })

    try:
        from backend.services.exchange_swap_rotation_service import (
            rotation_auto_execute_enabled,
            rotation_live_enabled,
        )

        rotation = {
            "auto_execute": rotation_auto_execute_enabled(),
            "live": rotation_live_enabled(),
        }
    except Exception:
        rotation = {}

    marketplace_users = 0
    try:
        import os
        from backend.services import agent_marketplace_service as mkt

        udir = mkt._USER_AGENTS_DIR
        if os.path.isdir(udir):
            marketplace_users = sum(1 for n in os.listdir(udir) if n.endswith(".json"))
    except Exception:
        pass

    try:
        from backend.services import casino_agents_service as cas

        casino_cfg = cas.load_config() if hasattr(cas, "load_config") else {}
    except Exception:
        casino_cfg = {}

    import os

    casino_dry = os.environ.get("CASINO_AGENT_DRY_RUN", "1").strip().lower() in ("1", "true", "yes")

    supervisors_paused = [
        s.get("id")
        for s in (controls.get("supervisors") or [])
        if not s.get("enabled", True)
    ]

    return {
        "success": True,
        "dormant_count": len(dormant),
        "dormant_agents": dormant[:80],
        "supervisors_paused": supervisors_paused,
        "rotation": rotation,
        "marketplace_users_with_agents": marketplace_users,
        "casino_dry_run": casino_dry,
        "scanned_at": _iso(),
    }


def activate_profit_stack(*, enable_rotation_auto: bool = True) -> Dict[str, Any]:
    """Enable profit supervisors + rotation auto (does not enable live gates or disable kill switch)."""
    from backend.services.trading_bots_control_service import _load_controls, _save_controls
    from backend.services.exchange_fleet_activation_service import activate_fleet_for_profit

    controls = _load_controls()
    if controls.get("kill_switch"):
        return {"success": False, "error": "kill_switch_active"}

    profit_sups = ("sup_arbitrage", "sup_winnable", "sup_extended", "sup_profit")
    enabled_sups: List[str] = []
    for s in controls.get("supervisors") or []:
        if s.get("id") in profit_sups and not s.get("enabled", True):
            s["enabled"] = True
            enabled_sups.append(str(s["id"]))

    activation = activate_fleet_for_profit(controls, enable_dormant=True)
    _save_controls(controls)

    rotation_patch: Dict[str, Any] = {}
    if enable_rotation_auto:
        try:
            from backend.services.exchange_swap_rotation_service import apply_fund_hot_rotation_preset

            rotation_patch = apply_fund_hot_rotation_preset(enable_auto=True)
        except Exception as exc:
            rotation_patch = {"error": str(exc)[:120]}

    ex._audit("activate_profit_stack", user_id="owner", supervisors=",".join(enabled_sups))
    return {
        "success": True,
        "supervisors_enabled": enabled_sups,
        "fleet_activation": activation,
        "rotation_config": rotation_patch,
        "note": "Live trading still requires EXCHANGE_ARBITRAGE_LIVE and venue credentials.",
    }
