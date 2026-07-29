"""Trader agent staking pool bootstrap (Stage 2)."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

_TRADER_RE = re.compile(r"^trader_agent_\d+$")


def is_trader_agent(user_id: str) -> bool:
    return bool(_TRADER_RE.match(str(user_id or "").strip()))


def _trader_ids() -> List[str]:
    from backend.services.agent_wallet_service import get_treasury
    count = int(get_treasury().get("trader_agent_count") or 6)
    return [f"trader_agent_{i + 1}" for i in range(max(1, count))]


def target_stake_for_agent(agent_id: str) -> float:
    """Deterministic per-agent target stake from config variance."""
    from backend.services.mn2_staking_service import get_config
    ta = get_config().get("trader_agents") or {}
    target = float(ta.get("target_stake_mn2") or 25000)
    variance = float(ta.get("stake_variance_mn2") or 10000)
    digest = hashlib.sha256(agent_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    offset = (bucket * 2.0 - 1.0) * variance
    return round(target + offset, 2)


def _sync_wallet_to_points(agent_id: str) -> None:
    """Move agent wallet MN2 into unified points before staking."""
    from backend.services.agent_wallet_service import get_balance
    import backend.services.mn2_staking_service as staking

    wallet_bal = get_balance(agent_id)
    if wallet_bal <= 0:
        return
    pts_bal, _ = staking.get_balances(agent_id)
    gap = round(wallet_bal - pts_bal, 8)
    if gap > 0:
        staking._points().add_points(agent_id, "mn2_balance", gap, source="agent_wallet_sync")


def join_trader_agents_to_pool(*, dry_run: bool = False) -> Dict[str, Any]:
    """Stake trader agents into the custodial pool up to per-agent targets."""
    import backend.services.mn2_staking_service as staking

    ta_cfg = staking.get_config().get("trader_agents") or {}
    if ta_cfg.get("enabled") is False:
        return {"success": False, "error": "trader_agents_disabled"}

    results: List[Dict[str, Any]] = []
    total_staked = 0.0

    for aid in _trader_ids():
        if not is_trader_agent(aid):
            continue
        target = target_stake_for_agent(aid)
        staking.accept_terms(aid)
        current = float(staking.get_stake(aid).get("staked") or 0)
        gap = round(target - current, 8)
        if gap <= 0:
            results.append({"agent_id": aid, "skipped": True, "staked": current})
            continue
        if not dry_run:
            _sync_wallet_to_points(aid)
        if dry_run:
            results.append({"agent_id": aid, "would_stake": gap})
            total_staked += gap
            continue
        r = staking.stake(aid, gap)
        if r.get("success"):
            total_staked += gap
            results.append({"agent_id": aid, "staked": gap})
        else:
            results.append({"agent_id": aid, "error": r.get("error")})

    return {"success": True, "total_staked_mn2": round(total_staked, 8), "results": results}


def list_trader_agents_status(*, follower_user_id: Optional[str] = None) -> Dict[str, Any]:
    """Status for trader staking agents + optional follower copy-trading state."""
    import backend.services.mn2_staking_service as staking
    from backend.services.mn2_copy_trading import _load as load_copy_trading

    agents: List[Dict[str, Any]] = []
    pool_total = 0.0
    for aid in _trader_ids():
        stake = staking.get_stake(aid)
        target = target_stake_for_agent(aid)
        staked = float(stake.get("staked") or 0)
        pool_total += staked
        agents.append({
            "agent_id": aid,
            "label": aid.replace("_", " ").title(),
            "staked_mn2": round(staked, 8),
            "target_staked_mn2": target,
            "total_rewards_mn2": float(stake.get("total_earned") or 0),
        })

    follower: Dict[str, Any] = {"following": False}
    uid = str(follower_user_id or "").strip()
    if uid and uid.lower() not in ("", "default_user", "anon", "anonymous", "guest"):
        cfg = (load_copy_trading().get("followers") or {}).get(uid)
        if isinstance(cfg, dict) and cfg.get("enabled") and cfg.get("leader_agent_id"):
            follower = {"following": True, "follower": cfg}

    ta_cfg = staking.get_config().get("trader_agents") or {}
    return {
        "success": True,
        "trader_agents": agents,
        "pool_staked_by_traders_mn2": round(pool_total, 8),
        "follower": follower,
        "copy_trading": {
            "default_scale": float(ta_cfg.get("default_copy_scale") or 0.25),
            "default_max_mn2_per_step": float(ta_cfg.get("default_copy_max_mn2") or 25),
        },
    }
