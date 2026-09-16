"""Feature 8: external market bridge for DOGE (and configured symbols) via swap rotation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services.exchange_ops_service import load_config


def suggest_external_bridge(symbol: Optional[str] = None) -> Dict[str, Any]:
    cfg = load_config()
    bridge_cfg = cfg.get("external_bridge") or {}
    if not bridge_cfg.get("enabled", True):
        return {"success": True, "skipped": True, "reason": "disabled"}

    symbols = [str(s).upper() for s in (bridge_cfg.get("symbols") or ["DOGE"])]
    if symbol:
        symbols = [symbol.upper()]

    from backend.services.exchange_swap_rotation_service import (
        rotation_live_enabled,
        suggest_swap_actions,
    )

    rot = suggest_swap_actions(limit=20)
    all_actions = rot.get("actions") or []
    suggestions: List[Dict[str, Any]] = []
    for sym in symbols:
        external = [
            a for a in all_actions
            if str(a.get("type") or "") in ("external_market_buy", "external_market_sell")
            and str(a.get("symbol") or "").upper() == sym
        ]
        suggestions.append({
            "symbol": sym,
            "venue": bridge_cfg.get("preferred_venue") or "nonkyc",
            "actions": external[:3],
            "rotation_live": rotation_live_enabled(),
        })

    return {
        "success": True,
        "symbols": symbols,
        "suggestions": suggestions,
        "live_enabled": rotation_live_enabled(),
    }


def execute_external_bridge(symbol: str, *, dry_run: bool = True) -> Dict[str, Any]:
    sym = (symbol or "DOGE").upper()
    plan = suggest_external_bridge(sym)
    if not plan.get("success"):
        return plan

    actions = []
    for item in plan.get("suggestions") or []:
        actions.extend(item.get("actions") or [])

    if not actions:
        return {"success": True, "skipped": True, "reason": "no_external_actions", "symbol": sym}

    if dry_run:
        return {"success": True, "dry_run": True, "symbol": sym, "actions": actions}

    from backend.services.exchange_swap_rotation_service import execute_rotation

    return execute_rotation(actions[0], dry_run=False)
