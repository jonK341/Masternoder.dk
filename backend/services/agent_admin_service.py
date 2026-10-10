"""Agents control board status and treasury reconciliation (Stage 3)."""
from __future__ import annotations

from typing import Any, Dict, List


def reconcile_treasury_pool() -> Dict[str, Any]:
    """Compare treasury pool balance vs trader agent wallet totals."""
    from backend.services.agent_wallet_service import (
        get_treasury,
        get_treasury_pool_balance,
        list_wallets,
    )

    treasury = get_treasury()
    per_agent = float(treasury.get("per_agent_mn2") or 100000)
    count = int(treasury.get("trader_agent_count") or 6)
    target_funded = round(per_agent * count, 8)
    wallet_sum = round(
        sum(
            float(w.get("mn2_balance") or 0)
            for w in list_wallets()
            if str(w.get("agent_id") or "").startswith("trader_agent_")
        ),
        8,
    )
    pool = round(get_treasury_pool_balance(), 8)
    return {
        "pool_balance_mn2": pool,
        "trader_wallet_sum_mn2": wallet_sum,
        "target_funded_mn2": target_funded,
        "funding_gap_mn2": round(max(0.0, target_funded - wallet_sum), 8),
        "ok": wallet_sum <= target_funded + 0.01,
    }


def get_control_status() -> Dict[str, Any]:
    """Aggregate status for the agents control board."""
    from backend.services.agent_kill_switch import get_status as kill_status
    from backend.services.agent_trader_service import list_strategies
    from backend.services.agent_trader_staking_service import list_trader_agents_status
    from backend.services.agent_wallet_service import (
        get_treasury,
        get_treasury_pool_balance,
        list_wallets,
    )

    treasury = get_treasury()
    traders = list_trader_agents_status()
    wallets: List[Dict[str, Any]] = []
    for w in list_wallets():
        if not str(w.get("agent_id") or "").startswith("trader_agent_"):
            continue
        aid = str(w.get("agent_id"))
        try:
            from backend.services.agent_trader_service import trader_level_for_agent
            w = dict(w)
            w["level"] = trader_level_for_agent(aid)
        except Exception:
            pass
        wallets.append(w)
    return {
        "success": True,
        "treasury": treasury,
        "pool_balance_mn2": get_treasury_pool_balance(),
        "required_total_mn2": float(treasury.get("per_agent_mn2") or 100000) * int(
            treasury.get("trader_agent_count") or 6
        ),
        "kill_switch": kill_status(),
        "trader_agents": traders.get("trader_agents") or [],
        "pool_staked_by_traders_mn2": traders.get("pool_staked_by_traders_mn2", 0),
        "strategies": list_strategies(),
        "trader_wallets": wallets,
        "reconcile": reconcile_treasury_pool(),
    }
