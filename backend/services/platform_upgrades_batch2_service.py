"""
Platform batch-2 upgrades (items 101–300) — catalog and per-area widget payloads.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BATCH2_PATH = os.path.join(_BASE, "data", "platform_upgrades_batch2.json")

_VALID_AREAS = {
    "explorer", "exchange", "profile", "shop", "casino",
    "generator", "command-center", "game", "quest", "battle",
}


def _load_batch2() -> Dict[str, Any]:
    if not os.path.exists(_BATCH2_PATH):
        return {"version": "", "batch": 2, "areas": []}
    try:
        with open(_BATCH2_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "", "batch": 2, "areas": []}


def get_batch2_roadmap(area: Optional[str] = None) -> Dict[str, Any]:
    catalog = _load_batch2()
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
                "ref_batch1": up.get("ref_batch1"),
            })
    return {
        "success": True,
        "batch": 2,
        "batch1_doc": catalog.get("batch1_doc", "PLATFORM_100_UPGRADES.md"),
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


def get_batch2_widgets(area: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    area = (area or "").strip().lower()
    if area not in _VALID_AREAS:
        return {"success": False, "error": "unknown area", "area": area}

    uid = _user_id(user_id)
    now = datetime.now(timezone.utc).isoformat()
    widgets: Dict[str, Any] = {"success": True, "area": area, "batch": 2, "user_id": uid, "updated_at": now}

    roadmap = get_batch2_roadmap(area)
    block = next((a for a in (roadmap.get("areas") or []) if a.get("id") == area), None)
    if block:
        ups = block.get("upgrades") or []
        widgets["batch2_done"] = sum(1 for u in ups if u.get("status") == "done")
        widgets["batch2_total"] = len(ups)

    if area == "explorer":
        def _ov():
            from backend.services.mn2_chainz import network_overview
            return network_overview()
        ov = _safe_call(_ov, {})
        daemon = (ov or {}).get("daemon") or {}
        widgets.update({
            "daemon_reachable": bool(daemon.get("reachable")),
            "staking_enabled": daemon.get("staking") or daemon.get("masternode_enabled"),
            "connections": daemon.get("connections"),
            "cache_age_sec": ov.get("cache_age_sec"),
            "mn2_usd_price": ov.get("mn2_usd_price"),
            "sparkline_blocks": (ov.get("history") or {}).get("block_heights", [])[-5:],
        })

    elif area == "exchange":
        def _stash():
            from backend.services.exchange_treasury_service import treasury_status
            return treasury_status()
        def _hot():
            from backend.services.exchange_profit_pair_search_service import ui_payload
            return ui_payload(refresh=False, limit=5)
        def _metrics():
            from backend.services.profit_daemon_ops_service import daemon_metrics_snapshot
            return daemon_metrics_snapshot()
        st = _safe_call(_stash, {})
        hot = _safe_call(_hot, {})
        met = _safe_call(_metrics, {})
        widgets.update({
            "live_stash_usd": st.get("live_stash_usd") or st.get("ledger_stashed_usd_live"),
            "paper_mode": met.get("mode") == "paper",
            "hot_symbols": hot.get("hot_symbols") or [],
            "profit_kill": bool(met.get("profit_kill")),
            "recent_stashes": (st.get("recent_stashes") or st.get("ledger_entries_list") or [])[:5],
            "tab_health": {"trade": True, "treasury": bool(st.get("success")), "bots": True},
        })

    elif area == "profile":
        def _ppp():
            from backend.services.exchange_profit_agent_skills_service import get_agent_profit_skills
            return get_agent_profit_skills("profit_oracle")
        def _pts():
            from backend.services.unified_points_database import unified_points_db
            if not unified_points_db:
                return {}
            raw = unified_points_db.get_all_points(uid) or {}
            return raw.get("points", raw) if isinstance(raw, dict) else {}
        def _rg():
            from backend.services.casino_responsible_gaming import status_for_user
            return status_for_user(uid)
        ppp = _safe_call(_ppp, {})
        pts = _safe_call(_pts, {})
        rg = _safe_call(_rg, {})
        widgets.update({
            "ppp_synced": bool((ppp.get("profile") or {}).get("agent_level")),
            "agent_level": (ppp.get("profile") or {}).get("agent_level"),
            "claimable_quests": pts.get("claimable_quests") or 0,
            "rg_daily_cap": rg.get("daily_cap"),
            "rg_bets_today": rg.get("bets_today"),
            "stats_links": [
                {"label": "Battle", "href": "/battle"},
                {"label": "Quests", "href": "/quests"},
                {"label": "Shop", "href": "/shop"},
                {"label": "Exchange", "href": "/exchange"},
            ],
        })

    elif area == "shop":
        def _deal_items():
            from datetime import datetime, timezone
            import hashlib
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            day_hash = int(hashlib.md5(today.encode()).hexdigest()[:6], 16)
            from backend.routes.shop_routes import _get_shop_items
            items = _get_shop_items()
            if not items:
                return {}
            item = items[day_hash % len(items)]
            original_price = item.get('price', 100)
            discount_pct = 25 + (day_hash % 16)
            deal_price = max(10, int(original_price * (1 - discount_pct / 100))) if isinstance(original_price, (int, float)) else original_price
            return {
                "date": today,
                "deal": {
                    "item_id": item.get("id"), "name": item.get("name"),
                    "original_price": original_price, "deal_price": deal_price,
                    "discount_pct": discount_pct,
                },
            }
        def _fulfill():
            from backend.services.shop_mn2_fulfillment_service import fulfillment_status_for_user
            return fulfillment_status_for_user(uid)
        deal = _safe_call(_deal_items, {})
        ful = _safe_call(_fulfill, {})
        widgets.update({
            "daily_deal": deal.get("deal"),
            "deal_date": deal.get("date"),
            "mn2_balance": ful.get("mn2_balance"),
            "fulfillment_status": ful.get("status"),
            "cart_count": 0,
        })

    elif area == "casino":
        def _bridge():
            from backend.services.exchange_user_controller_service import hub_state
            import backend.services.casino_service as casino_service
            hub = hub_state(uid)
            bal = casino_service.get_balance(uid)
            return {
                "casino_coins": bal.get("coins") if isinstance(bal, dict) else None,
                "mn2_balance": hub.get("mn2_balance") if isinstance(hub, dict) else None,
                "jackpot_coins": bal.get("jackpot_pool") if isinstance(bal, dict) else None,
            }
        def _ticks():
            from backend.services.casino_agents_service import tick_summary
            return tick_summary(hours=6, limit=50)
        def _rg():
            from backend.services.casino_responsible_gaming import status_for_user
            return status_for_user(uid)
        bridge = _safe_call(_bridge, {})
        ticks = _safe_call(_ticks, {})
        rg = _safe_call(_rg, {})
        widgets.update({
            "exchange_bridge": bridge,
            "tick_summary": {
                "wins": ticks.get("wins"),
                "losses": ticks.get("losses"),
                "win_rate_pct": ticks.get("win_rate_pct"),
                "agents_active": ticks.get("agents_active"),
            },
            "rg": rg,
            "jackpot_pool": bridge.get("jackpot_coins") or 10000,
            "house_edge_pct": 2.5,
        })

    elif area == "generator":
        def _queue():
            from backend.routes.missing_endpoints_routes import generator_queue_status
            return generator_queue_status().get_json()
        def _health():
            from backend.routes.missing_endpoints_routes import generator_generation_health
            return generator_generation_health().get_json()
        def _credits():
            from backend.services.unified_points_database import unified_points_db
            if not unified_points_db:
                return {}
            raw = unified_points_db.get_all_points(uid) or {}
            pts = raw.get("points", raw) if isinstance(raw, dict) else {}
            return {"generation_credits": pts.get("generation_credits") or pts.get("generation_points", 0) / 100}
        queue = _safe_call(_queue, {})
        health = _safe_call(_health, {})
        cred = _safe_call(_credits, {})
        widgets.update({
            "queue_depth": queue.get("queue_depth") or queue.get("pending") or 0,
            "api_ready": bool(health.get("ready")),
            "generation_credits": cred.get("generation_credits"),
            "providers": health.get("providers") or ["default"],
        })

    elif area == "command-center":
        def _top25():
            from backend.services.exchange_profit_agent_skills_service import critical_problems_top25
            return critical_problems_top25(refresh=False, dynamic=False)
        def _metrics():
            from backend.services.profit_daemon_ops_service import daemon_metrics_snapshot
            return daemon_metrics_snapshot()
        def _treasury():
            from backend.services.exchange_treasury_service import treasury_status
            return treasury_status()
        top = _safe_call(_top25, {})
        met = _safe_call(_metrics, {})
        tre = _safe_call(_treasury, {})
        open_p = [i for i in (top.get("items") or top.get("problems") or []) if not (i.get("done") or i.get("checked"))]
        widgets.update({
            "top25_open": len(open_p),
            "top25_p0": sum(1 for i in open_p if str(i.get("priority", "")).upper() in ("P0", "CRITICAL")),
            "profit_kill": bool(met.get("profit_kill")),
            "treasury_usd": tre.get("total_stash_usd") or tre.get("ledger_stashed_usd"),
            "generator_queue_alert": False,
            "quick_actions": [
                {"label": "Quick battle", "href": "/battle#quick-battle"},
                {"label": "Profit daemon", "href": "/profit/"},
                {"label": "Exchange", "href": "/exchange/"},
            ],
        })

    elif area == "game":
        def _hub():
            from backend.services.game_hub_service import get_overview
            return get_overview(uid)
        hub = _safe_call(_hub, {})
        game_tab = (hub.get("tabs") or {}).get("game") or {}
        widgets.update({
            "level": game_tab.get("level"),
            "xp": game_tab.get("xp_total"),
            "claimable": (hub.get("tabs") or {}).get("quests", {}).get("claimable", 0),
            "champion_pulse": hub.get("champion_pulse") or now,
            "nexus_link": "/game#campaign",
            "starmap_link": "/starmap25",
        })

    elif area == "quest":
        def _hub():
            from backend.services.game_hub_service import get_overview
            return get_overview(uid)
        def _streak():
            from backend.services.trophy_quest_service import get_unified_quests
            data = get_unified_quests(uid)
            return data.get("claim_streak") or {}
        hub = _safe_call(_hub, {})
        streak = _safe_call(_streak, {})
        qtab = (hub.get("tabs") or {}).get("quests") or {}
        widgets.update({
            "active_quests": qtab.get("active") or 0,
            "claimable": qtab.get("claimable") or 0,
            "streak_days": (streak.get("days") if isinstance(streak, dict) else None) or qtab.get("claim_streak", {}).get("days"),
            "ppp_sync": True,
            "daily_reset_utc": "00:00",
            "quest_types": ["daily", "battle", "profit", "generator"],
        })

    elif area == "battle":
        def _stats():
            from backend.routes.battle_routes import _get_battle_stats
            return _get_battle_stats(uid)
        def _lb():
            from backend.routes.battle_routes import _leaderboard_payload
            return _leaderboard_payload()
        stats = _safe_call(_stats, {})
        lb = _safe_call(_lb, {})
        widgets.update({
            "stats": stats,
            "leaderboard_top3": (lb.get("leaderboard") or lb.get("entries") or [])[:3],
            "matchmaking_queue": stats.get("matchmaking_queue") or 0,
            "win_streak": stats.get("battle_streak") or stats.get("win_streak") or 0,
            "mn2_per_win": 0.01,
            "quick_battle_href": "/battle#quick-battle",
            "recommended_difficulty": stats.get("recommended_difficulty") or "normal",
        })

    from backend.services.platform_batch2_extras_service import enrich_area_widgets
    enrich_area_widgets(area, widgets, uid)
    return widgets
