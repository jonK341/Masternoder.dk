"""Fleet roster skill sets — profit + monetization edges for supervisor bots."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services import exchange_bot_skills_service as sk

# Ten fleet-roster monetization skills (ids must exist in data/exchange_bot_skills.json).
FLEET_ROSTER_SKILL_IDS: List[str] = [
    "hot_lane_snipe",
    "ppp_edge_scan",
    "stream_revenue_cross_sell",
    "tip_conversion_nudge",
    "paypal_rail_optimizer",
    "casino_exchange_bridge",
    "affiliate_spread_capture",
    "rental_yield_boost",
    "subscription_tier_ladder",
    "margin_floor_guard",
]

FLEET_ROSTER_SKILL_SET_ID = "fleet_roster_monetization"

_KIND_EXTRA_SKILLS: Dict[str, List[str]] = {
    "analytics": ["spatial_arbitrage", "withdrawal_aware_routing", "kelly_sizing"],
    "extended_profit": ["internal_rebalance", "stablecoin_peg", "latency_twap"],
    "treasury": ["inventory_band", "maker_rebate_harvest"],
    "risk": ["withdrawal_aware_routing", "inventory_band"],
    "winnable_pairs": ["spatial_arbitrage", "hot_lane_snipe"],
}


def fleet_skill_ids_for_bot(bot: Dict[str, Any]) -> List[str]:
    kind = str(bot.get("kind") or "")
    extra = list(_KIND_EXTRA_SKILLS.get(kind) or [])
    merged = list(dict.fromkeys(extra + FLEET_ROSTER_SKILL_IDS))
    cfg = bot.get("config") or {}
    custom = cfg.get("skills") or bot.get("skills")
    if isinstance(custom, list) and custom:
        merged = list(dict.fromkeys([str(s) for s in custom] + merged))
    return merged


def enrich_fleet_bot_skills(bot: Dict[str, Any], *, volatility: float = 0.38) -> Dict[str, Any]:
    ids = fleet_skill_ids_for_bot(bot)
    ss = sk.resolve_skill_set(FLEET_ROSTER_SKILL_SET_ID, ids, volatility=volatility)
    bot["skills"] = ids
    bot["skill_set"] = ss["id"]
    bot["skill_meta"] = {
        "name": ss["name"],
        "tier": ss.get("tier"),
        "skill_count": ss["skill_count"],
        "blended_edge_bps": ss["blended_edge_bps"],
        "monetization_stream": "fleet-roster-skills",
    }
    bot["skill_details"] = ss["skill_details"]
    return bot


def blended_edge_bps(bot: Dict[str, Any], *, volatility: float = 0.38) -> float:
    meta = bot.get("skill_meta") or {}
    if meta.get("blended_edge_bps") is not None:
        return float(meta["blended_edge_bps"])
    ids = fleet_skill_ids_for_bot(bot)
    return float(sk.blended_edge_bps(ids, volatility).get("blended_edge_bps") or 0)


def profit_execution_threshold_bps(bot: Dict[str, Any], *, base: float = 10.0) -> float:
    """Lower net_bps bar when fleet monetization skills stack higher edge."""
    edge = blended_edge_bps(bot)
    # Up to ~4 bps easier threshold at ~80+ blended edge.
    adj = min(4.0, edge / 22.0)
    return round(max(5.0, base - adj), 2)


def fleet_skills_catalog() -> Dict[str, Any]:
    details = sk.skill_details(FLEET_ROSTER_SKILL_IDS, volatility=0.38)
    ss = sk.resolve_skill_set(FLEET_ROSTER_SKILL_SET_ID, FLEET_ROSTER_SKILL_IDS, volatility=0.38)
    return {
        "skill_set_id": FLEET_ROSTER_SKILL_SET_ID,
        "skill_ids": list(FLEET_ROSTER_SKILL_IDS),
        "skill_count": len(FLEET_ROSTER_SKILL_IDS),
        "skills": details,
        "skill_set": {
            "id": ss["id"],
            "name": ss["name"],
            "tier": ss.get("tier"),
            "description": ss.get("description"),
            "blended_edge_bps": ss["blended_edge_bps"],
        },
        "monetization_stream_id": "fleet-roster-skills",
    }


def fleet_monetization_snapshot(bots: List[Dict[str, Any]], *, volatility: float = 0.38) -> Dict[str, Any]:
    edges = [blended_edge_bps(b, volatility=volatility) for b in bots]
    total_edge = round(sum(edges), 2)
    avg_edge = round(total_edge / len(edges), 2) if edges else 0.0
    # Coarse operator estimate: micro-notional fleet × edge bps → monthly uplift band (not financial advice).
    micro = 75.0
    est_monthly = round((total_edge / 10000.0) * micro * max(1, len(bots)) * 4.3, 2)
    return {
        "stream_id": "fleet-roster-skills",
        "stream_name": "Fleet roster skill monetization",
        "bot_count": len(bots),
        "total_blended_edge_bps": total_edge,
        "avg_blended_edge_bps": avg_edge,
        "estimated_monthly_uplift_usd": est_monthly,
        "note": "Estimate from roster skill edges × micro-notional ticks; enable fleet + live rails for real revenue.",
    }


def assign_skills_to_fleet_controls(controls: Dict[str, Any]) -> None:
    for b in controls.get("fleet_bots") or []:
        enrich_fleet_bot_skills(b)
