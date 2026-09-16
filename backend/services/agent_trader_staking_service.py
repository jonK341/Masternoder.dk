"""Trader agent staking pool helpers and profile status."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

import backend.services.mn2_staking_service as staking


def _trader_cfg() -> Dict[str, Any]:
    cfg = staking.get_config()
    ta = cfg.get("trader_agents") if isinstance(cfg.get("trader_agents"), dict) else {}
    return ta


def is_trader_agent(user_id: str) -> bool:
    return str(user_id or "").strip().startswith("trader_agent_")


def _trader_agent_ids() -> List[str]:
    count = 6
    try:
        from backend.services.agent_wallet_service import get_treasury

        count = int(get_treasury().get("trader_agent_count") or 6)
    except Exception:
        pass
    return [f"trader_agent_{i + 1}" for i in range(max(0, count))]


def target_stake_for_agent(agent_id: str) -> float:
    cfg = _trader_cfg()
    base = float(cfg.get("target_stake_mn2") or 25000)
    variance = float(cfg.get("stake_variance_mn2") or 10000)
    digest = hashlib.md5(str(agent_id or "").encode(), usedforsecurity=False).hexdigest()[:8]
    frac = int(digest, 16) / 0xFFFFFFFF
    return round((base - variance) + (2 * variance * frac), 8)


def _sync_trader_wallet_balance(agent_id: str) -> None:
    """Move agent-wallet MN2 into the staking points ledger when needed."""
    try:
        from backend.services.agent_wallet_service import get_balance as agent_wallet_balance

        wallet_bal = float(agent_wallet_balance(agent_id) or 0)
        bal, _ = staking.get_balances(agent_id)
        if wallet_bal > bal:
            staking._points().add_points(
                agent_id,
                "mn2_balance",
                round(wallet_bal - bal, 8),
                source="trader_wallet_fund",
            )
    except Exception:
        pass


def join_trader_agents_to_pool(dry_run: bool = False) -> Dict[str, Any]:
    cfg = _trader_cfg()
    if cfg.get("enabled") is False:
        return {"success": False, "error": "trader_agents disabled"}
    total = 0.0
    results: List[Dict[str, Any]] = []
    for aid in _trader_agent_ids():
        target = target_stake_for_agent(aid)
        st = staking.get_stake(aid)
        current = float(st.get("staked") or 0)
        need = max(0.0, target - current)
        if need <= 0:
            results.append({"agent_id": aid, "skipped": True, "staked_mn2": current})
            continue
        if dry_run:
            results.append({"agent_id": aid, "dry_run": True, "amount": need})
            total += need
            continue
        if not staking.has_accepted_terms(aid):
            staking.accept_terms(aid)
        _sync_trader_wallet_balance(aid)
        out = staking.stake(aid, need)
        results.append({"agent_id": aid, **out})
        if out.get("success"):
            total += need
    return {"success": True, "total_staked_mn2": round(total, 8), "results": results}


def list_trader_agents_status(follower_user_id: Optional[str] = None) -> Dict[str, Any]:
    cfg = _trader_cfg()
    agents: List[Dict[str, Any]] = []
    pool_total = 0.0
    for aid in _trader_agent_ids():
        st = staking.get_stake(aid)
        staked = float(st.get("staked") or 0)
        target = target_stake_for_agent(aid)
        pool_total += staked
        agents.append(
            {
                "agent_id": aid,
                "label": aid.replace("_", " ").title(),
                "staked_mn2": staked,
                "target_staked_mn2": target,
                "total_rewards_mn2": float(st.get("total_earned") or 0),
            }
        )

    follower: Dict[str, Any] = {"following": False}
    if follower_user_id:
        import backend.services.mn2_copy_trading as copy_trade

        data = copy_trade._load()
        fcfg = (data.get("followers") or {}).get(str(follower_user_id).strip())
        if isinstance(fcfg, dict) and fcfg.get("enabled"):
            follower = {"following": True, "follower": fcfg}
        else:
            follower = {"following": False}

    return {
        "success": True,
        "trader_agents": agents,
        "pool_staked_by_traders_mn2": round(pool_total, 8),
        "follower": follower,
        "copy_trading": {
            "default_scale": float(cfg.get("default_scale") or 0.25),
            "default_max_mn2_per_step": float(cfg.get("default_max_mn2_per_step") or 25),
        },
    }
