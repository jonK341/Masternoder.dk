"""Unified live trading monitor — one feed users can follow the whole trading process from.

Aggregates, for a user:
  - their owned bots (level, intelligence/IQ, game time, last action, learning mastery),
  - a live activity feed merged from the hash-chained audit log (their own bot profits,
    purchases, crypto buys, achievements + global market arbitrage prints),
  - headline totals (realized profit, active bots, avg intelligence, total game time).
"""
from __future__ import annotations

from typing import Any, Dict, List

from backend.services import crypto_exchange_service as ex

_FEED_ACTIONS = {
    "agent_paper_profit", "agent_purchased", "paypal_crypto_capture",
    "arbitrage_paper_trade", "leveling_achievement", "leveling_level_claim",
    "payout_sweep", "trust_agent_activation", "trust_controls_updated",
}
_GLOBAL_ACTIONS = {"arbitrage_paper_trade"}


def _label(rec: Dict[str, Any]) -> Dict[str, Any]:
    action = rec.get("action") or ""
    data = rec.get("data") or {}
    amt = float(rec.get("amount_usd") or 0)
    if action == "agent_paper_profit":
        return {"icon": "🤖", "kind": "bot_profit",
                "text": f"Bot {str(data.get('agent_id') or '')[:10]} earned ${amt:.2f}"}
    if action == "arbitrage_paper_trade":
        return {"icon": "🔀", "kind": "arbitrage",
                "text": f"Arb {data.get('symbol','')}: {data.get('buy_venue','')}→{data.get('sell_venue','')} +${amt:.2f} ({data.get('net_bps','?')} bps)"}
    if action == "agent_purchased":
        return {"icon": "🛒", "kind": "purchase",
                "text": f"Bought agent {data.get('template_id','')}"}
    if action == "paypal_crypto_capture":
        return {"icon": "🪙", "kind": "buy",
                "text": f"Bought {data.get('asset_amount','')} {data.get('symbol','')} (${amt:.2f})"}
    if action == "leveling_achievement":
        return {"icon": "🏅", "kind": "achievement",
                "text": f"Achievement unlocked: {data.get('achievement','')}"}
    if action == "leveling_level_claim":
        return {"icon": "⬆️", "kind": "level",
                "text": f"Claimed level {data.get('level','')} reward"}
    if action == "payout_sweep":
        return {"icon": "🏦", "kind": "sweep",
                "text": f"Stashed ${amt:.2f} {data.get('stash_asset','')} to Binance ({data.get('mode','')})"}
    if action == "trust_agent_activation":
        return {"icon": "🔐", "kind": "trust",
                "text": f"Agent {str(data.get('agent_id') or '')[:10]} → {data.get('activation','')}"}
    if action == "trust_controls_updated":
        return {"icon": "⚙️", "kind": "trust", "text": "Trust controls updated"}
    return {"icon": "•", "kind": action, "text": action}


def live_monitor(user_id: str, *, feed_limit: int = 40) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    from backend.services import agent_marketplace_service as mkt
    try:
        from backend.services import exchange_agent_learning_service as learn
        from backend.services import exchange_trust_service as trust_svc
    except Exception:
        learn = None
        trust_svc = None

    portfolio = mkt.user_portfolio(user_id) if user_id else {"agents": [], "total_realized_profit_usd": 0.0}
    agents = portfolio.get("agents") or []
    ut_score = trust_svc.compute_user_trust(user_id)["score"] if trust_svc and user_id else 0

    bots: List[Dict[str, Any]] = []
    total_game_time = 0
    intel_vals = []
    trust_vals = []
    for a in agents:
        snap = learn.learning_snapshot(a) if learn else {}
        tp = trust_svc.agent_trust_profile(user_id, a, user_trust=ut_score) if trust_svc else {}
        total_game_time += int(a.get("game_time_sec") or 0)
        iq = tp.get("composite_iq") or a.get("intelligence") or snap.get("intelligence") or 100
        intel_vals.append(float(iq))
        trust_vals.append(float(tp.get("trust_score") or a.get("trust_score") or 0))
        bots.append({
            "agent_id": a.get("agent_id"), "name": a.get("name"), "tier": a.get("tier"),
            "enabled": a.get("enabled", True), "super": bool(a.get("super")),
            "agent_level": a.get("agent_level") or 1, "intelligence": iq,
            "trust_score": tp.get("trust_score") or 0, "activation": tp.get("activation") or a.get("activation"),
            "can_run": tp.get("can_run", False),
            "mastery_pct": a.get("mastery_pct") or snap.get("mastery_pct") or 0,
            "game_time_sec": int(a.get("game_time_sec") or 0),
            "realized_profit_usd": round(float(a.get("realized_profit_usd") or 0), 4),
            "trade_count": a.get("trade_count") or 0,
            "learning_bonus_bps": a.get("learning_bonus_bps") or 0,
            "top_skills": snap.get("top_skills") or [],
            "last_action": a.get("last_action"),
        })

    tail = ex.get_audit_tail(limit=400).get("records") or []
    feed: List[Dict[str, Any]] = []
    for rec in tail:
        action = rec.get("action") or ""
        if action not in _FEED_ACTIONS:
            continue
        is_global = action in _GLOBAL_ACTIONS
        if not is_global and (rec.get("user_id") or "") != user_id:
            continue
        item = _label(rec)
        item.update({"ts": rec.get("ts"), "amount_usd": round(float(rec.get("amount_usd") or 0), 4),
                     "scope": "market" if is_global else "you"})
        feed.append(item)
        if len(feed) >= feed_limit:
            break

    avg_intel = round(sum(intel_vals) / len(intel_vals), 1) if intel_vals else 100.0
    avg_trust = round(sum(trust_vals) / len(trust_vals), 1) if trust_vals else 0.0
    user_trust = trust_svc.compute_user_trust(user_id) if trust_svc and user_id else {"score": 0, "tier": {"name": "—"}}
    return {
        "success": True,
        "user_id": user_id,
        "user_trust": user_trust,
        "totals": {
            "realized_profit_usd": round(float(portfolio.get("total_realized_profit_usd") or 0), 4),
            "active_bots": sum(1 for b in bots if b["enabled"]),
            "bot_count": len(bots),
            "avg_intelligence": avg_intel,
            "avg_trust": avg_trust,
            "total_game_time_sec": total_game_time,
            "projected_daily_usd": round(float((portfolio.get("projection") or {}).get("combined_daily_profit_usd") or 0), 4),
        },
        "bots": sorted(bots, key=lambda b: b["realized_profit_usd"], reverse=True),
        "feed": feed,
    }
