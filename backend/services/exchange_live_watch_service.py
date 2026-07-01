"""Live Watch — review console for trust, intelligence, activations, and trading activity.

User view: own bots + trust profile + feed (wraps live_monitor + trust).
Owner view (admin): all users with agents, policy controls, global feed, suspend/activate.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_trust_service as trust


def user_live_watch(user_id: str, *, feed_limit: int = 50) -> Dict[str, Any]:
    from backend.services.exchange_trading_monitor_service import live_monitor
    from backend.services import agent_marketplace_service as mkt

    user_id = (user_id or "").strip()
    profile = trust.user_trust_profile(user_id)
    mon = live_monitor(user_id, feed_limit=feed_limit)
    agents_raw = mkt.list_user_agents(user_id).get("agents") or []
    agents: List[Dict[str, Any]] = []
    for a in agents_raw:
        tp = trust.agent_trust_profile(user_id, a, user_trust=profile["trust_score"])
        agents.append({**a, **tp})

    active = sum(1 for a in agents if a.get("activation") == "active")
    pending = sum(1 for a in agents if a.get("activation") == "pending")
    return {
        "success": True,
        "scope": "user",
        "user_id": user_id,
        "trust": profile,
        "totals": {
            **(mon.get("totals") or {}),
            "avg_trust": round(sum(a.get("trust_score", 0) for a in agents) / len(agents), 1) if agents else 0,
            "avg_composite_iq": round(sum(a.get("composite_iq", 100) for a in agents) / len(agents), 1) if agents else 100,
            "active_agents": active,
            "pending_activation": pending,
        },
        "agents": agents,
        "feed": mon.get("feed") or [],
    }


def owner_live_watch(*, feed_limit: int = 80) -> Dict[str, Any]:
    from backend.services import agent_marketplace_service as mkt

    udir = mkt._USER_AGENTS_DIR
    rows: List[Dict[str, Any]] = []
    if os.path.isdir(udir):
        for name in os.listdir(udir):
            if not name.endswith(".json"):
                continue
            uid = name[:-5]
            try:
                w = user_live_watch(uid, feed_limit=20)
                if w.get("agents"):
                    rows.append({
                        "user_id": uid,
                        "trust_score": w["trust"]["trust_score"],
                        "tier": w["trust"]["tier"],
                        "agent_count": len(w["agents"]),
                        "active_agents": w["totals"].get("active_agents", 0),
                        "pending_activation": w["totals"].get("pending_activation", 0),
                        "realized_profit_usd": w["totals"].get("realized_profit_usd", 0),
                        "avg_composite_iq": w["totals"].get("avg_composite_iq", 100),
                        "agents": w["agents"],
                    })
            except Exception:
                continue

    rows.sort(key=lambda r: r.get("realized_profit_usd") or 0, reverse=True)
    tail = ex.get_audit_tail(limit=300).get("records") or []
    feed: List[Dict[str, Any]] = []
    trust_actions = {"trust_agent_activation", "trust_controls_updated", "trust_policy_updated",
                     "agent_paper_profit", "arbitrage_paper_trade", "agent_purchased", "payout_sweep"}
    for rec in tail:
        if (rec.get("action") or "") not in trust_actions:
            continue
        feed.append({
            "ts": rec.get("ts"), "action": rec.get("action"), "user_id": rec.get("user_id"),
            "amount_usd": rec.get("amount_usd"), "data": rec.get("data") or {},
        })
        if len(feed) >= feed_limit:
            break

    policy = trust._policy()
    return {
        "success": True,
        "scope": "owner",
        "policy": policy,
        "user_count": len(rows),
        "users": rows,
        "feed": feed,
        "totals": {
            "users": len(rows),
            "agents": sum(r["agent_count"] for r in rows),
            "active_agents": sum(r["active_agents"] for r in rows),
            "pending_activation": sum(r["pending_activation"] for r in rows),
        },
    }
