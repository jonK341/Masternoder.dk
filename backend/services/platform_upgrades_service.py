"""
Platform 100-upgrade roadmap — load catalog and aggregate per-area widget summaries.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CATALOG_PATH = os.path.join(_BASE, "data", "platform_upgrades.json")

_VALID_AREAS = {
    "explorer", "exchange", "profile", "shop", "casino",
    "generator", "command-center", "game", "quest", "battle",
}


def _load_catalog() -> Dict[str, Any]:
    if not os.path.exists(_CATALOG_PATH):
        return {"version": "", "areas": []}
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "", "areas": []}


def get_roadmap(area: Optional[str] = None) -> Dict[str, Any]:
    catalog = _load_catalog()
    areas = catalog.get("areas") or []
    if area:
        area = area.strip().lower()
        areas = [a for a in areas if a.get("id") == area]
    items: List[Dict[str, Any]] = []
    done = planned = 0
    for block in areas:
        for up in block.get("upgrades") or []:
            st = (up.get("status") or "planned").lower()
            if st == "done":
                done += 1
            else:
                planned += 1
            items.append({
                "id": up.get("id"),
                "area": block.get("id"),
                "area_name": block.get("name"),
                "title": up.get("title"),
                "priority": up.get("priority", "P3"),
                "status": st,
            })
    return {
        "success": True,
        "version": catalog.get("version"),
        "total": len(items),
        "done": done,
        "planned": planned,
        "areas": areas,
        "items": items,
    }


def _safe_call(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _user_id(user_id: Optional[str]) -> str:
    return (user_id or "default_user").strip() or "default_user"


def get_area_summary(area: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    area = (area or "").strip().lower()
    if area not in _VALID_AREAS:
        return {"success": False, "error": "unknown area", "area": area}

    uid = _user_id(user_id)
    now = datetime.now(timezone.utc).isoformat()
    summary: Dict[str, Any] = {"success": True, "area": area, "user_id": uid, "updated_at": now}

    if area == "explorer":
        def _explorer():
            from backend.services.mn2_chainz import network_overview
            return network_overview()
        ov = _safe_call(_explorer, {})
        daemon = (ov or {}).get("daemon") or {}
        summary.update({
            "block_height": ov.get("block_height"),
            "mn2_usd_price": ov.get("mn2_usd_price"),
            "daemon_reachable": bool(daemon.get("reachable")),
            "cache_source": (ov.get("source") or {}).get("block_height", "api"),
            "masternode_count": ov.get("masternode_count"),
        })

    elif area == "exchange":
        def _stash():
            from backend.services.exchange_treasury_service import treasury_status
            return treasury_status()
        st = _safe_call(_stash, {})
        summary.update({
            "live_stash_usd": st.get("live_stash_usd") or st.get("ledger_stashed_usd_live"),
            "paper_stash_usd": st.get("paper_stash_usd") or st.get("ledger_stashed_usd_paper"),
            "total_stash_usd": st.get("total_stash_usd") or st.get("ledger_stashed_usd"),
            "profit_link": "/profit/",
            "oracle_link": "/exchange/#cex-profit-oracle",
        })

    elif area == "profile":
        def _points():
            from backend.services.unified_points_database import unified_points_db
            if not unified_points_db:
                return {}
            raw = unified_points_db.get_all_points(uid) or {}
            return raw.get("points", raw) if isinstance(raw, dict) else {}
        def _mn2():
            from backend.services.mn2_wallet_service import get_balance
            return get_balance(uid)
        def _ppp_level():
            from backend.services.exchange_profit_agent_skills_service import get_agent_profit_skills
            data = get_agent_profit_skills("profit_oracle")
            profile = (data or {}).get("profile") or {}
            return profile.get("agent_level") or profile.get("level")
        pts = _safe_call(_points, {})
        bal = _safe_call(_mn2, {})
        lvl = _safe_call(_ppp_level)
        summary.update({
            "level": pts.get("level") or pts.get("game_level"),
            "xp": pts.get("xp_total") or pts.get("xp"),
            "coins": pts.get("coins") or pts.get("total_coins"),
            "mn2_balance": bal.get("mn2_balance") if isinstance(bal, dict) else None,
            "agent_level": lvl,
            "ppp_synced": lvl is not None,
        })

    elif area == "shop":
        def _price():
            from backend.services.mn2_chainz import mn2_usd_price_median
            bundle = mn2_usd_price_median()
            return bundle.get("price") if isinstance(bundle, dict) else bundle
        summary.update({
            "mn2_usd_price": _safe_call(_price),
            "daily_deal_endpoint": "/api/shop/daily-deal",
            "cart_key": f"shop_cart_v2_{uid}",
        })

    elif area == "casino":
        def _rg():
            from backend.services.casino_responsible_gaming import status_for_user
            return status_for_user(uid)
        rg = _safe_call(_rg, {})
        summary.update({
            "responsible_gaming": rg,
            "profit_link": "/profit/",
            "agent_control_link": "/exchange/#cex-control-center",
        })

    elif area == "generator":
        def _health():
            from backend.routes.missing_endpoints_routes import generator_generation_health
            return generator_generation_health().get_json()
        def _queue():
            from backend.routes.missing_endpoints_routes import generator_queue_status
            return generator_queue_status().get_json()
        health = _safe_call(_health, {})
        queue = _safe_call(_queue, {})
        summary.update({
            "api_ready": bool(health.get("ready")),
            "api_message": health.get("message"),
            "queue_depth": queue.get("queue_depth") or queue.get("pending"),
            "history_endpoint": "/api/generator/history",
        })

    elif area == "command-center":
        def _top25():
            from backend.services.exchange_profit_agent_skills_service import critical_problems_top25
            return critical_problems_top25(refresh=False, dynamic=False)
        def _daemon():
            from backend.services.mn2_chainz import network_overview
            ov = network_overview()
            dm = (ov or {}).get("daemon") or {}
            return {"reachable": dm.get("reachable"), "connections": dm.get("connections")}
        top = _safe_call(_top25, {})
        dm = _safe_call(_daemon, {})
        open_count = 0
        done_count = 0
        for item in (top.get("items") or top.get("problems") or []):
            if item.get("done") or item.get("checked"):
                done_count += 1
            else:
                open_count += 1
        summary.update({
            "daemon_reachable": bool(dm.get("reachable")),
            "daemon_connections": dm.get("connections"),
            "top25_open": open_count,
            "top25_done": done_count,
            "top25_total": open_count + done_count,
        })

    elif area == "game":
        def _hub():
            from backend.services.game_hub_service import get_overview
            return get_overview(uid)
        hub = _safe_call(_hub, {})
        game_tab = (hub.get("tabs") or {}).get("game") or {}
        summary.update({
            "level": game_tab.get("level") or game_tab.get("hunter_level"),
            "xp": game_tab.get("xp_total") or game_tab.get("hunter_xp"),
            "coins": game_tab.get("game_points"),
            "online_estimate": hub.get("online_count") or 1,
            "featured": [
                {"title": "Hunter Nexus", "href": "/game#campaign"},
                {"title": "Star Map 25", "href": "/starmap25"},
                {"title": "Battle", "href": "/battle"},
                {"title": "Quests", "href": "/quests"},
            ],
        })

    elif area == "quest":
        def _hub():
            from backend.services.game_hub_service import get_overview
            return get_overview(uid)
        hub = _safe_call(_hub, {})
        qtab = (hub.get("tabs") or {}).get("quests") or {}
        quests = qtab.get("quests") or []
        summary.update({
            "active_quests": qtab.get("active") or len([q for q in quests if not q.get("claimed")]),
            "claimable": qtab.get("claimable") or 0,
            "streak": qtab.get("claim_streak") or (hub.get("summary") or {}).get("claim_streak"),
            "ppp_sync": True,
        })

    elif area == "battle":
        def _hub():
            from backend.services.game_hub_service import get_overview
            return get_overview(uid)
        def _lb():
            from backend.routes.battle_routes import _leaderboard_payload
            return _leaderboard_payload()
        def _stats():
            from backend.routes.battle_routes import _get_battle_stats
            return _get_battle_stats(uid)
        hub = _safe_call(_hub, {})
        btab = (hub.get("tabs") or {}).get("battle") or {}
        lb = _safe_call(_lb, {})
        summary.update({
            "leaderboard": (lb.get("leaderboard") or lb.get("entries") or [])[:5],
            "recent_matches": btab.get("recent_matches") or [],
            "stats": _safe_call(_stats, {}),
            "enter_battle_href": "/battle#quick-battle",
        })

    roadmap = get_roadmap(area)
    block = next((a for a in (roadmap.get("areas") or []) if a.get("id") == area), None)
    if block:
        ups = block.get("upgrades") or []
        summary["upgrades_done"] = sum(1 for u in ups if u.get("status") == "done")
        summary["upgrades_total"] = len(ups)

    return summary
