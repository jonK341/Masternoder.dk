"""Trader agent staking pool bootstrap — stake treasury-funded agents into MN2 pool."""
from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List, Optional

import backend.services.mn2_staking_agents_service as staking_agents
import backend.services.mn2_staking_service as staking
from backend.services.agent_wallet_service import get_balance as agent_wallet_balance, get_treasury


def _trader_cfg() -> Dict[str, Any]:
    cfg = staking.get_config()
    ta = cfg.get("trader_agents") if isinstance(cfg.get("trader_agents"), dict) else {}
    return ta


def trader_agent_ids() -> List[str]:
    treasury = get_treasury()
    count = int(treasury.get("trader_agent_count") or 6)
    return [f"trader_agent_{i + 1}" for i in range(count)]


def is_trader_agent(user_id: str) -> bool:
    uid = (user_id or "").strip()
    return uid.startswith("trader_agent_") and uid in trader_agent_ids()


def target_stake_for_agent(agent_id: str) -> float:
    ta = _trader_cfg()
    base = float(ta.get("target_stake_mn2") or 25000)
    variance = int(ta.get("stake_variance_mn2") or 10000)
    h = int(hashlib.sha256(agent_id.encode("utf-8")).hexdigest()[:8], 16)
    jitter = (h % (2 * variance + 1)) - variance
    minimum = float(ta.get("min_target_stake_mn2") or 1000)
    return round(max(minimum, base + jitter), 8)


def sync_trader_wallet_to_points(agent_id: str) -> Dict[str, Any]:
    """Align unified_points mn2_balance with agent_wallets ledger for a trader agent."""
    agent_id = (agent_id or "").strip()
    wallet_bal = agent_wallet_balance(agent_id)
    bal, _staked = staking.get_balances(agent_id)
    delta = round(wallet_bal - bal, 8)
    if abs(delta) < 1e-8:
        return {"success": True, "agent_id": agent_id, "synced": False, "balance": wallet_bal}
    r = staking._points().add_points(
        agent_id,
        "mn2_balance",
        delta,
        source="agent_wallet_sync",
        metadata={"reference": f"wallet-sync:{agent_id}", "agent_id": agent_id},
    )
    return {
        "success": bool(r.get("success", True)),
        "agent_id": agent_id,
        "synced": not r.get("duplicate"),
        "delta": delta,
        "balance": wallet_bal,
    }


def _policy_for_agent(agent_id: str, target: float) -> Dict[str, Any]:
    ta = _trader_cfg()
    keep = float(ta.get("keep_balance_min_mn2") or 5000)
    return {
        "enabled": True,
        "target_staked": target,
        "max_staked": round(target * float(ta.get("max_staked_multiplier") or 1.15), 8),
        "keep_balance_min": keep,
        "auto_compound": bool(ta.get("auto_compound", True)),
        "heartbeat": bool(ta.get("heartbeat", True)),
        "auto_accept_terms": True,
        "allowed_actions": ["accept_terms", "heartbeat", "set_auto_compound", "stake", "unstake"],
        "rebalance_step_max": float(ta.get("rebalance_step_max_mn2") or 0),
    }


def join_trader_agents_to_pool(*, dry_run: bool = False) -> Dict[str, Any]:
    """Sync wallets, accept terms, set policies, stake ~25k±10k per trader agent."""
    ta = _trader_cfg()
    if not bool(ta.get("enabled", True)):
        return {"success": False, "error": "trader_agents disabled in config"}

    results: List[Dict[str, Any]] = []
    total_staked = 0.0

    for aid in trader_agent_ids():
        target = target_stake_for_agent(aid)
        row: Dict[str, Any] = {"agent_id": aid, "target_staked": target}

        if dry_run:
            wallet = agent_wallet_balance(aid)
            cur = staking.get_stake(aid)
            staked = float(cur.get("staked") or 0)
            gap = round(max(0.0, target - staked), 8)
            row.update({
                "dry_run": True,
                "wallet_balance": wallet,
                "staked": staked,
                "would_stake": min(gap, max(0.0, wallet - float(ta.get("keep_balance_min_mn2") or 5000))),
            })
            results.append(row)
            continue

        sync_trader_wallet_to_points(aid)
        if not staking.has_accepted_terms(aid):
            staking.accept_terms(aid)

        staking_agents.upsert_agent(aid, aid, policy=_policy_for_agent(aid, target))

        cur = staking.get_stake(aid)
        staked = float(cur.get("staked") or 0)
        gap = round(max(0.0, target - staked), 8)
        keep = float(ta.get("keep_balance_min_mn2") or 5000)
        free = max(0.0, float(cur.get("mn2_balance") or 0) - keep)
        amt = round(min(gap, free), 8)

        if amt <= 0:
            row.update({"skipped": True, "reason": "already_at_target_or_insufficient_free", "staked": staked})
            results.append(row)
            continue

        res = staking.stake(aid, amt)
        row.update({"staked_amount": amt, "result": res})
        if res.get("success"):
            staking_agents._tag_managed(aid, aid)
            total_staked += amt
            try:
                from backend.services.mn2_copy_trading import mirror_agent_run
                mirror_agent_run(aid, aid, [{"action": "stake", "amount": amt, "result": res}])
            except Exception:
                pass
        results.append(row)

    return {
        "success": True,
        "dry_run": dry_run,
        "agents": len(results),
        "total_staked_mn2": round(total_staked, 8),
        "results": results,
    }


def list_trader_agents_status(*, follower_user_id: Optional[str] = None) -> Dict[str, Any]:
    """Public status for profile dashboard + optional follower copy-trade state."""
    agents_out: List[Dict[str, Any]] = []
    pool_staked = 0.0
    for aid in trader_agent_ids():
        target = target_stake_for_agent(aid)
        try:
            st = staking.get_stake(aid)
            wallet = agent_wallet_balance(aid)
            staked = float(st.get("staked") or 0)
            pool_staked += staked
            agents_out.append({
                "agent_id": aid,
                "label": aid.replace("_", " ").title(),
                "wallet_balance_mn2": wallet,
                "staked_mn2": staked,
                "target_staked_mn2": target,
                "available_mn2": float(st.get("mn2_balance") or 0),
                "total_rewards_mn2": float(st.get("total_earned") or 0),
                "terms_accepted": bool(st.get("terms_accepted")),
                "managed": bool(st.get("managed_by_agent") or st.get("managed")),
            })
        except Exception as exc:
            agents_out.append({
                "agent_id": aid,
                "label": aid.replace("_", " ").title(),
                "error": str(exc),
                "wallet_balance_mn2": 0.0,
                "staked_mn2": 0.0,
                "target_staked_mn2": target,
                "available_mn2": 0.0,
                "total_rewards_mn2": 0.0,
                "terms_accepted": False,
                "managed": False,
            })

    follower: Dict[str, Any] = {"following": False}
    if follower_user_id:
        try:
            from backend.services.mn2_copy_trading import get_follower
            follower = get_follower(follower_user_id)
        except Exception:
            pass

    ta = _trader_cfg()
    return {
        "success": True,
        "trader_agents": agents_out,
        "pool_staked_by_traders_mn2": round(pool_staked, 8),
        "target_stake_mn2": float(ta.get("target_stake_mn2") or 25000),
        "stake_variance_mn2": int(ta.get("stake_variance_mn2") or 10000),
        "follower": follower,
        "copy_trading": {
            "follow_endpoint": "/api/mn2/copy-trading/follow",
            "unfollow_endpoint": "/api/mn2/copy-trading/unfollow",
            "default_scale": float(ta.get("default_follow_scale") or 0.25),
            "default_max_mn2_per_step": float(ta.get("default_max_mn2_per_step") or 25),
        },
    }
