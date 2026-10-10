"""Point system control board — unified status for 178 systems integration."""
from __future__ import annotations

from typing import Any, Dict, List


def get_board_status() -> Dict[str, Any]:
    systems: List[Dict[str, Any]] = []

    def _check(name: str, fn) -> None:
        ok, err = True, None
        try:
            fn()
        except Exception as exc:
            ok, err = False, str(exc)[:120]
        systems.append({"name": name, "ok": ok, "error": err})

    _check("unified_points", lambda: __import__("backend.services.unified_points_database", fromlist=["unified_points_db"]).unified_points_db)
    _check("p2p_market", lambda: __import__("backend.services.p2p_market_service", fromlist=["list_orders"]).list_orders())
    _check("agent_wallets", lambda: __import__("backend.services.agent_wallet_service", fromlist=["list_wallets"]).list_wallets())
    _check("activity_events", lambda: __import__("backend.services.activity_events_service", fromlist=["recent"]).recent(limit=1))
    _check("game_rewards", lambda: __import__("backend.services.game_mn2_rewards", fromlist=["credit_mn2"]))

    return {"success": True, "systems": systems, "healthy": all(s["ok"] for s in systems)}
