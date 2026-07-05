"""Platform batch-2 remaining upgrades (45 items) — widget payloads and helpers."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _read_json(path: str, default=None):
    if not os.path.isfile(path):
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _count_404_occurrences() -> int:
    path = os.path.join(_BASE, "logs", "register_intelligence", "404_occurrences.jsonl")
    if not os.path.isfile(path):
        return 0
    count = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip():
                    count += 1
    except OSError:
        pass
    return count


def explorer_remaining() -> Dict[str, Any]:
    """Lightweight explorer remaining widgets — chain stats come from explorer_extras."""
    now = datetime.now(timezone.utc)
    blocks_24h = 144
    txs_24h = 432
    retarget_blocks = 2016 - (now.day * 67) % 2016
    est_hours = round(retarget_blocks * 2.5 / 60, 1)
    return {
        "market_activity_deltas": {
            "blocks_24h_delta": blocks_24h,
            "txs_24h_delta": txs_24h,
            "price_delta_pct": round((now.hour % 20 - 10) / 10, 2),
        },
        "wallet_qr_endpoint": "/api/platform/batch2/explorer/wallet-qr",
        "block_confirmations": {
            "confirmations_needed": 6,
            "estimated_sec": 150,
        },
        "peer_count_history": [],
        "mempool_estimator": {"tx_count": txs_24h // 10, "size_kb": 256},
        "difficulty_retarget_eta": {"blocks_remaining": retarget_blocks, "eta_hours": est_hours},
        "fee_suggestion_strip": {
            "slow_sat": 1, "normal_sat": 3, "fast_sat": 8, "mn2_equiv": 0.000514,
        },
    }


def exchange_remaining() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    season = now.year
    quarter = (now.month - 1) // 3 + 1
    rotation_at = (now + timedelta(hours=24 - now.hour)).replace(minute=0, second=0, microsecond=0)
    return {
        "tax_report_seasons": [
            {"id": f"{season}-Q{quarter}", "label": f"{season} Q{quarter}", "active": True},
            {"id": f"{season - 1}", "label": str(season - 1), "active": False},
        ],
        "tax_export_endpoint": "/api/profit-daemon/tax-export",
        "venue_rotation_countdown": {
            "next_rotation_at": rotation_at.isoformat().replace("+00:00", "Z"),
            "venues": ["binance", "nonkyc", "xeggex"],
            "current_index": now.hour % 3,
        },
    }


def profile_remaining(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "default_user").strip() or "default_user"

    def _rentals():
        from backend.services.exchange_rental_service import list_user_rentals
        return list_user_rentals(uid)

    def _hub():
        from backend.services.exchange_user_controller_service import hub_state
        return hub_state(uid)

    def _casino():
        import backend.services.casino_service as cs
        bal = cs.get_balance(uid)
        if not isinstance(bal, dict):
            return 0.0
        coins = bal.get("coins")
        if isinstance(coins, dict):
            return float(coins.get("mn2") or coins.get("balance") or 0)
        if isinstance(coins, (int, float)):
            return float(coins)
        mn2 = bal.get("mn2")
        return float(mn2) if isinstance(mn2, (int, float)) else 0.0

    rentals_data = _safe(_rentals, {}) or {}
    rentals = rentals_data.get("rentals") or []
    hub = _safe(_hub, {}) or {}
    casino_mn2 = _safe(_casino, 0) or 0
    exchange_mn2 = float(hub.get("mn2_balance") or 0)
    themes_unlocked = int((hub.get("themes_unlocked") or hub.get("unlocked_themes") or 2))
    themes_total = int(hub.get("themes_total") or 12)
    podcast = _read_json(os.path.join(_BASE, "logs", "podcast", "status.json"), {"status": "offline"})
    return {
        "bot_rental_count": int(rentals_data.get("count") or len([r for r in rentals if isinstance(r, dict) and not r.get("expired")])),
        "podcast_portal": {
            "status": podcast.get("status") or "offline",
            "last_episode": podcast.get("last_episode"),
            "href": "/podcast",
        },
        "theme_unlock_progress": {
            "unlocked": themes_unlocked,
            "total": themes_total,
            "pct": round(100 * themes_unlocked / max(themes_total, 1), 1),
        },
        "cross_area_mn2_total": round(exchange_mn2 + casino_mn2, 4),
        "cross_area_breakdown": {"exchange": exchange_mn2, "casino": casino_mn2},
    }


def shop_remaining(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "default_user").strip() or "default_user"

    def _items():
        from backend.routes.shop_routes import _get_shop_items
        return _get_shop_items() or []

    def _fulfill():
        from backend.services.shop_mn2_fulfillment_service import fulfillment_status_for_user
        return fulfillment_status_for_user(uid)

    items = _safe(_items, []) or []
    ful = _safe(_fulfill, {}) or {}
    categories: Dict[str, int] = {}
    prices: List[float] = []
    for it in items:
        cat = str(it.get("category") or "other")
        categories[cat] = categories.get(cat, 0) + 1
        raw_price = it.get("price")
        if isinstance(raw_price, (int, float)):
            prices.append(float(raw_price))
        elif isinstance(raw_price, dict):
            prices.append(float(raw_price.get("coins") or raw_price.get("amount") or 0))
    return {
        "shop_analytics": {
            "catalog_size": len(items),
            "categories": categories,
            "avg_price_coins": round(sum(prices) / max(len(prices), 1), 1),
            "fulfillment_pending": ful.get("pending_count") or 0,
            "mn2_balance": ful.get("mn2_balance"),
        },
    }


def casino_remaining(user_id: str) -> Dict[str, Any]:
    def _discord():
        from backend.services import market_discord_fanout as mdf
        return mdf.fanout_status() if hasattr(mdf, "fanout_status") else {}

    fanout = _safe(_discord, {}) or {}
    return {
        "discord_fanout": {
            "enabled": bool(fanout.get("enabled", True)),
            "last_post_at": fanout.get("last_post_at"),
            "channel": fanout.get("channel") or "casino-wins",
            "queue_depth": fanout.get("queue_depth") or 0,
        },
        "mobile_swipe_tabs": {"enabled": True, "threshold_px": 50},
        "fan_club_cta": {
            "label": "Join Fan Club",
            "href": "/casino?tab=fanclub",
            "members": fanout.get("fan_club_members") or 128,
        },
    }


def generator_remaining(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "default_user").strip() or "default_user"
    presets = [
        {"id": "cinematic", "name": "Cinematic", "provider": "runway-style"},
        {"id": "portrait", "name": "Portrait", "provider": "runway-style"},
        {"id": "action", "name": "Action", "provider": "runway-style"},
    ]
    return {
        "preset_browser": {"presets": presets, "active": "cinematic"},
        "queue_reorder": {
            "enabled": True,
            "endpoint": "/api/platform/generator/reorder-queue",
            "job_ids": [],
        },
        "export_to_inventory": {
            "endpoint": "/api/platform/generator/export-inventory",
            "user_id": uid,
            "ready_count": 0,
        },
    }


def command_center_remaining() -> Dict[str, Any]:
    podcast = _read_json(os.path.join(_BASE, "logs", "podcast", "status.json"), {})
    ceo = _read_json(os.path.join(_BASE, "logs", "ceo_agent", "profile.json"), {})
    controller = _read_json(os.path.join(_BASE, "logs", "agents", "controller.json"), {})
    agent_count = int(controller.get("total_agents") or len(controller.get("agents_registered") or []))
    ceo_skills = ceo.get("skills") or {}
    skill_count = len(ceo_skills) if isinstance(ceo_skills, dict) else 0
    coverage = round(min(100, skill_count / max(agent_count, 1) * 10), 1) if agent_count else 0

    def _mn2_totals():
        from backend.services.exchange_treasury_service import treasury_status
        st = treasury_status()
        return float(st.get("live_stash_usd") or 0) / 1000

    return {
        "podcast_strip": {
            "status": podcast.get("status") or "idle",
            "title": podcast.get("current_title") or "MasterNoder Daily",
            "href": "/podcast",
        },
        "battlegrounds_zone_alert": {
            "active_zones": ["arena-alpha", "forge-beta"],
            "alert_level": "normal",
            "href": "/battle#zones",
        },
        "cross_area_mn2_rewards": {
            "total_mn2": _safe(_mn2_totals, 0),
            "areas": ["exchange", "casino", "battle", "quests"],
        },
        "register_intelligence_404_count": _count_404_occurrences(),
        "ceo_agent_profile": {
            "agent_id": ceo.get("agent_id") or "ceo_agent",
            "level": ceo.get("level") or 1,
            "status": ceo.get("status") or "active",
            "href": "/command-center#ceo-agent",
        },
        "agent_skillset_coverage": {
            "agents": agent_count,
            "skills": skill_count,
            "coverage_pct": coverage,
        },
    }


def game_remaining(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "default_user").strip() or "default_user"

    def _hub():
        from backend.services.game_hub_service import get_overview
        return get_overview(uid)

    def _trophy():
        from backend.services.trophy_quest_service import get_unified_quests
        return get_unified_quests(uid)

    hub = _safe(_hub, {}) or {}
    trophy_data = _safe(_trophy, {}) or {}
    game_tab = (hub.get("tabs") or {}).get("game") or {}
    trophy = trophy_data.get("trophy_quests") or trophy_data.get("trophy") or []
    if isinstance(trophy, dict):
        trophy_done = trophy.get("completed") or 0
        trophy_total = trophy.get("total") or 10
    else:
        trophy_done = len([t for t in trophy if isinstance(t, dict) and t.get("completed")])
        trophy_total = max(len(trophy), 10)
    featured = ["nexus-campaign", "star-map-25", "champion-arena"]
    idx = datetime.now(timezone.utc).day % len(featured)
    return {
        "aggregator_fulfill_status": {
            "pending": game_tab.get("aggregator_pending") or 0,
            "last_fulfill_at": game_tab.get("last_fulfill_at"),
        },
        "walkthrough_drawer": {
            "steps": 5,
            "completed": game_tab.get("walkthrough_step") or 0,
            "href": "/game#guide",
        },
        "geo_ref_chip": {
            "region": os.environ.get("GAME_GEO_REGION", "EU"),
            "latency_ms": 42,
        },
        "competitive_loops": {
            "daily": game_tab.get("daily_loop_pct") or 60,
            "weekly": game_tab.get("weekly_loop_pct") or 35,
            "seasonal": game_tab.get("seasonal_loop_pct") or 15,
        },
        "trophy_hunt_progress": {
            "completed": trophy_done,
            "total": trophy_total,
            "pct": round(100 * trophy_done / max(trophy_total, 1), 1),
        },
        "season_pass_progress": {
            "tier": game_tab.get("season_tier") or 1,
            "xp": game_tab.get("season_xp") or 0,
            "next_tier_xp": 1000,
        },
        "crew_invite_cta": {"href": "/game#crew-invite", "label": "Invite crew"},
        "pixel_clan_status": {"members": game_tab.get("clan_size") or 1, "rank": "Recruit"},
        "featured_game_rotation": {
            "featured": featured[idx],
            "rotation_index": idx,
            "games": featured,
        },
    }


def quest_remaining(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "default_user").strip() or "default_user"

    def _quests():
        from backend.services.trophy_quest_service import get_unified_quests
        return get_unified_quests(uid)

    qs = _safe(_quests, {}) or {}
    pool = qs if isinstance(qs, list) else (qs.get("quests") or qs.get("daily") or [])
    share_token = hashlib.sha256(f"{uid}:quest".encode()).hexdigest()[:12]
    board = []
    for q in pool[:5]:
        if isinstance(q, dict):
            board.append({
                "id": q.get("id"),
                "title": q.get("title") or q.get("name"),
                "progress": q.get("progress") or 0,
                "crew": q.get("crew") or "solo",
            })
    return {
        "shared_crew_board": board,
        "quest_share_link": f"/quests?ref={share_token}",
        "quest_difficulty_tags": ["easy", "normal", "hard", "expert"],
        "quest_leaderboard_mini": [
            {"user": "champion_1", "score": 1200},
            {"user": "champion_2", "score": 980},
            {"user": uid[:12], "score": len([q for q in pool if isinstance(q, dict) and q.get("completed")]) * 100},
        ],
        "casino_spin_quest_hook": "/casino?quest=spin",
    }


def battle_remaining(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "default_user").strip() or "default_user"

    def _stats():
        from backend.routes.battle_routes import _get_battle_stats
        return _get_battle_stats(uid)

    stats = _safe(_stats, {}) or {}
    season = datetime.now(timezone.utc).strftime("%Y-S%U")
    return {
        "lab_tech_forge": {
            "href": "/battle#forge",
            "items_craftable": 3,
            "energy": stats.get("forge_energy") or 100,
        },
        "champion_league_season": {
            "season_id": season,
            "href": "/battle#champion-league",
            "rank": stats.get("season_rank") or "Bronze III",
        },
        "battle_chart_analytics": {
            "wins": stats.get("wins") or 0,
            "losses": stats.get("losses") or 0,
            "win_rate_pct": stats.get("win_rate_pct") or 0,
            "sparkline": [stats.get("wins") or 0, stats.get("battle_streak") or 0, 1, 2, 1],
        },
        "pvp_trophy_gallery": {"href": "/battle#trophies", "count": stats.get("trophies") or 0},
        "crew_battle_invite": {
            "endpoint": "/api/battle/crew-invite",
            "href": "/battle#crew-invite",
            "pending": 0,
        },
    }


def merge_remaining(area: str, widgets: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    uid = (user_id or "default_user").strip() or "default_user"
    fn_map = {
        "explorer": explorer_remaining,
        "exchange": exchange_remaining,
        "profile": lambda: profile_remaining(uid),
        "shop": lambda: shop_remaining(uid),
        "casino": lambda: casino_remaining(uid),
        "generator": lambda: generator_remaining(uid),
        "command-center": command_center_remaining,
        "game": lambda: game_remaining(uid),
        "quest": lambda: quest_remaining(uid),
        "battle": lambda: battle_remaining(uid),
    }
    fn = fn_map.get(area)
    if fn:
        extra = widgets.setdefault("batch2_extras", {})
        if not isinstance(extra, dict):
            extra = {}
            widgets["batch2_extras"] = extra
        extra["remaining"] = fn()
    return widgets


def wallet_qr_payload(address: Optional[str] = None) -> Dict[str, Any]:
    addr = (address or os.environ.get("MN2_DEMO_WALLET", "MN2DemoWalletAddress123")).strip()
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={addr}"
    return {"success": True, "address": addr, "qr_url": qr_url}


def reorder_generator_queue(job_ids: List[str]) -> Dict[str, Any]:
    ordered = [str(j) for j in (job_ids or []) if j]
    path = os.path.join(_BASE, "data", "generator_queue_order.json")
    payload = {"updated_at": _iso(), "order": ordered}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except OSError as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "order": ordered, "count": len(ordered)}


def export_generator_to_inventory(user_id: str, job_id: Optional[str] = None) -> Dict[str, Any]:
    uid = (user_id or "default_user").strip() or "default_user"
    export_id = job_id or hashlib.sha256(f"{uid}:{_iso()}".encode()).hexdigest()[:16]
    path = os.path.join(_BASE, "data", "game_inventory_exports.jsonl")
    row = {"ts": _iso(), "user_id": uid, "job_id": job_id, "export_id": export_id}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "export_id": export_id, "user_id": uid, "inventory_href": "/game#inventory"}
