"""Gate C readiness checks — Stage 2 market + trader agents + treasury distribution."""
from __future__ import annotations

from typing import Any, Dict, List


def _check(name: str, fn) -> Dict[str, Any]:
    try:
        ok = bool(fn())
        return {"name": name, "ok": ok}
    except Exception as exc:
        return {"name": name, "ok": False, "error": str(exc)}


def check_gate_c() -> Dict[str, Any]:
    """Return Gate C component status for ops/health endpoints."""
    checks: List[Dict[str, Any]] = []

    def trader_service_ok() -> bool:
        from backend.services.agent_trader_service import list_strategies, run_all_traders
        strategies = list_strategies()
        return len(strategies) >= 4 and callable(run_all_traders)

    def trader_staking_ok() -> bool:
        from backend.services.agent_trader_staking_service import (
            join_trader_agents_to_pool,
            list_trader_agents_status,
            target_stake_for_agent,
        )
        r = list_trader_agents_status()
        return (
            r.get("success") is True
            and isinstance(r.get("trader_agents"), list)
            and callable(join_trader_agents_to_pool)
            and target_stake_for_agent("trader_agent_1") > 0
        )

    def treasury_distribution_ok() -> bool:
        from backend.services.agent_wallet_service import (
            distribute_agent_funding,
            get_treasury,
            get_treasury_pool_balance,
        )
        t = get_treasury()
        return (
            isinstance(t, dict)
            and callable(distribute_agent_funding)
            and isinstance(get_treasury_pool_balance(), (int, float))
        )

    def internal_market_ok() -> bool:
        from backend.services.p2p_market_service import create_order, fill_order, list_orders
        r = list_orders()
        return (
            r.get("success") is True
            and callable(create_order)
            and callable(fill_order)
        )

    def copy_trading_ok() -> bool:
        from backend.services.mn2_copy_trading import mirror_leader_reward, upsert_follower
        return callable(mirror_leader_reward) and callable(upsert_follower)

    def agent_cron_ok() -> bool:
        from backend.services.agent_cron_service import expand_preset
        trader = expand_preset("trader")
        treasury = expand_preset("treasury")
        return "agent_trader" in trader and "treasury_distribute" in treasury

    def deposit_scanner_hook_ok() -> bool:
        from backend.services.mn2_deposit_scanner import maybe_distribute_treasury_after_deposit
        return callable(maybe_distribute_treasury_after_deposit)

    def activity_events_ok() -> bool:
        from backend.services.activity_events_service import emit
        for event in ("p2p_market_fill", "agent_funded", "trader_market_tick"):
            r = emit(event, channel="market", payload={"gate_c_probe": True})
            if r.get("success") is not True:
                return False
        return True

    def gate_b_ok() -> bool:
        from backend.services.gate_b_status_service import check_gate_b
        return check_gate_b().get("ready_for_stage_2") is True

    checks.append(_check("agent_trader_service", trader_service_ok))
    checks.append(_check("agent_trader_staking", trader_staking_ok))
    checks.append(_check("treasury_distribution", treasury_distribution_ok))
    checks.append(_check("internal_p2p_market", internal_market_ok))
    checks.append(_check("copy_trading_rewards", copy_trading_ok))
    checks.append(_check("agent_cron_presets", agent_cron_ok))
    checks.append(_check("deposit_scanner_distribute_hook", deposit_scanner_hook_ok))
    checks.append(_check("activity_events", activity_events_ok))
    checks.append(_check("gate_b_prerequisite", gate_b_ok))

    all_ok = all(c.get("ok") for c in checks)
    return {
        "success": True,
        "gate": "C",
        "status": "ready" if all_ok else "degraded",
        "ready_for_stage_3": all_ok,
        "checks": checks,
    }
