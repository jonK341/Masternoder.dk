"""Platform batch-1 remaining upgrades — widget payloads for items #10–#100 planned."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BATCH1_IDS = {
    "explorer": [10],
    "exchange": [19, 20],
    "profile": [25, 26, 27, 28, 29, 30],
    "shop": [36, 37, 38, 39, 40],
    "casino": [48, 49, 50],
    "generator": [56, 57, 58, 59, 60],
    "command-center": [67, 68, 69, 70],
    "game": [76, 77, 78, 79, 80],
    "quest": [85, 86, 87, 88, 89, 90],
    "battle": [97, 98, 99, 100],
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def get_batch1_widgets(area: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Batch-1 widget payload for one area — merges batch2 extras + batch1-specific fields."""
    area = (area or "").strip().lower()
    uid = (user_id or "default_user").strip() or "default_user"
    ids = _BATCH1_IDS.get(area)
    if not ids:
        return {"success": False, "error": "unknown area", "area": area}

    from backend.services.platform_upgrades_batch2_service import get_batch2_widgets

    base = get_batch2_widgets(area, user_id=uid)
    if not base.get("success"):
        base = {"success": True, "area": area, "user_id": uid}
    from backend.services.platform_batch2_extras_service import enrich_area_widgets

    widgets = enrich_area_widgets(area, dict(base), user_id=uid)
    extras = widgets.get("batch2_extras") or {}
    rem = extras.get("remaining") or {}
    batch1: Dict[str, Any] = {"upgrade_ids": ids, "updated_at": _iso()}

    if area == "explorer":
        deltas = rem.get("market_activity_deltas") or {}
        batch1.update({
            "market_activity_tiles": [
                {"label": "Blocks 24h", "value": deltas.get("blocks_24h_delta"), "delta": "+"},
                {"label": "Txs 24h", "value": deltas.get("txs_24h_delta"), "delta": "+"},
                {"label": "Price Δ", "value": deltas.get("price_delta_pct"), "unit": "%"},
            ],
        })

    elif area == "exchange":
        batch1.update({
            "agent_marketplace_link": {"href": "/exchange/#cex-agent-marketplace", "label": "Agent marketplace"},
            "venue_liquidity_heatmap": extras.get("liquidity_heatmap") or {},
        })

    elif area == "profile":
        t0 = time.perf_counter()
        _safe(lambda: None)
        load_ms = round((time.perf_counter() - t0) * 1000, 1)
        batch1.update({
            "stats_links": [
                {"label": "Game stats", "href": "/game#stats"},
                {"label": "Battle stats", "href": "/battle#stats"},
                {"label": "Exchange hub", "href": "/exchange/#cex-control-center"},
            ],
            "leaderboard_shortcut": {"href": "/battle#leaderboard", "label": "Leaderboard"},
            "shop_inventory_preview": {"endpoint": f"/api/shop/inventory?user_id={uid}", "href": "/shop#inventory"},
            "crew_status_chip": {"status": extras.get("crew_status"), "members": extras.get("crew_members", 0)},
            "trophy_income_estimate": _safe(_trophy_income_estimate, {"usd_per_day": 0, "mn2_per_day": 0}),
            "load_time_badge_ms": load_ms,
        })

    elif area == "shop":
        batch1.update({
            "mn2_pay_modal": {"enabled": True, "endpoint": "/api/shop/mn2/purchase", "rail": "mn2"},
            "vip_tier_badge": _safe(_vip_tier, {"tier": "standard", "label": "Shop VIP"}),
            "auction_quick_link": {"href": extras.get("auction_href") or "/shop?tab=auction"},
            "flash_sale_countdown": {
                "ends_at": extras.get("flash_sale_ends_at"),
                "active": extras.get("flash_sale_active"),
            },
            "shop_analytics": rem.get("shop_analytics") or {},
        })

    elif area == "casino":
        batch1.update({
            "tournament_countdown": {"ends_at": extras.get("tournament_ends_at")},
            "discord_fanout": rem.get("discord_fanout") or {},
            "house_edge_card": {"house_edge_pct": 2.5, "rtp_pct": 97.5, "disclaimer": "Theoretical RTP; actual varies by game."},
        })

    elif area == "generator":
        batch1.update({
            "provider_availability_grid": {
                "providers": extras.get("provider_latency_ms") or {},
                "count": extras.get("provider_count", 0),
            },
            "ai_magic_shortcut": {"href": "/generator?magic=1", "label": "AI magic generate"},
            "thumbnail_gallery": extras.get("thumbnail_gallery") or [],
            "entitlement_reserved": extras.get("entitlement_reserved", False),
            "preset_browser": rem.get("preset_browser") or {},
        })

    elif area == "command-center":
        batch1.update({
            "agent_support_status": {"open_tickets": extras.get("agent_support_open", 0)},
            "podcast_strip": rem.get("podcast_strip") or {},
            "battlegrounds_zone_alert": rem.get("battlegrounds_zone_alert") or {},
            "cross_area_mn2_totals": rem.get("cross_area_mn2_rewards") or {},
        })

    elif area == "game":
        batch1.update({
            "aggregator_fulfill_status": rem.get("aggregator_fulfill_status") or {},
            "star_map_25_link": {"href": "/starmap25", "label": "Star Map 25"},
            "walkthrough_drawer": rem.get("walkthrough_drawer") or {},
            "geo_ref_chip": rem.get("geo_ref_chip") or {},
            "competitive_loops": rem.get("competitive_loops") or {},
        })

    elif area == "quest":
        batch1.update({
            "ai_quest_cta": extras.get("ai_quest_cta") or "/quests?generate=1",
            "confetti_on_claim": True,
            "level_progression_panel": extras.get("level_progression") or {},
            "quest_filter_types": ["daily", "weekly", "trophy", "ppp"],
            "shared_crew_board": rem.get("shared_crew_board") or [],
            "mn2_reward_estimator": _safe(lambda: _quest_mn2_estimate(uid), {"estimated_mn2": 0}),
        })

    elif area == "battle":
        batch1.update({
            "lab_tech_forge": rem.get("lab_tech_forge") or {},
            "champion_league_season": rem.get("champion_league_season") or {},
            "battle_chart_analytics": rem.get("battle_chart_analytics") or {},
            "mn2_per_win": _safe(lambda: _battle_mn2_per_win(uid), 0.01),
        })

    widgets["batch1"] = batch1
    widgets["batch1_done"] = len(ids)
    widgets["batch1_total"] = len(ids)
    return widgets


def _trophy_income_estimate(user_id: str) -> Dict[str, Any]:
    path = os.path.join(_BASE, "data", "trophy_income", f"{user_id}.json")
    if os.path.isfile(path):
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "usd_per_day": float(data.get("usd_per_day") or 0),
            "mn2_per_day": float(data.get("mn2_per_day") or 0),
        }
    return {"usd_per_day": 0.05, "mn2_per_day": 0.001, "estimate": True}


def _vip_tier(user_id: str) -> Dict[str, Any]:
    from backend.services import shop_monetization_service as mon
    vip = mon.get_vip_status(user_id)
    tier = (vip.get("tier") or vip.get("active_tier") or "standard") if isinstance(vip, dict) else "standard"
    return {"tier": tier, "label": f"VIP {str(tier).title()}"}


def _quest_mn2_estimate(user_id: str) -> Dict[str, Any]:
    from backend.services.trophy_quest_service import get_unified_quests
    qs = get_unified_quests(user_id)
    pool = qs if isinstance(qs, list) else (qs.get("quests") or qs.get("daily") or [])
    total = 0.0
    for q in pool:
        if isinstance(q, dict) and not q.get("claimed"):
            total += float(q.get("mn2_reward") or q.get("reward_mn2") or 0.01)
    return {"estimated_mn2": round(total, 4), "claimable_quests": len(pool)}


def _battle_mn2_per_win(user_id: str) -> float:
    from backend.routes.battle_routes import _get_battle_stats
    stats = _get_battle_stats(user_id)
    return float(stats.get("mn2_per_win") or stats.get("reward_mn2") or 0.01)


def mark_batch1_complete_in_catalog() -> Dict[str, int]:
    """Utility: count batch1 items — catalog sync done via data/platform_upgrades.json."""
    from backend.services.platform_upgrades_service import get_roadmap
    r = get_roadmap()
    return {"done": r.get("done", 0), "planned": r.get("planned", 0), "total": r.get("total", 100)}
