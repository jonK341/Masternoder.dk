"""Casino super-experience hub — aggregates games, jackpots, events, social CTAs, user state."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "casino_hub_config.json")


def _load_hub_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _today_iso_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _live_stats() -> Dict[str, Any]:
    """Lightweight feel metrics from recent ledger activity."""
    from backend.services import casino_ledger

    online_feel = 0
    mn2_prizes_today = 0.0
    bets_today = 0
    prefix = _today_iso_prefix()
    try:
        wins = casino_ledger.recent_wins(limit=50)
        users = set()
        for row in wins:
            uid = row.get("user_id")
            if uid:
                users.add(str(uid))
            created = str(row.get("created_at") or "")
            if not created.startswith(prefix):
                continue
            bets_today += 1
            if str(row.get("currency") or "").lower() == "mn2" and float(row.get("net") or 0) > 0:
                mn2_prizes_today += float(row.get("net") or 0)
        online_feel = max(len(users), min(bets_today, 99))
        if online_feel == 0 and wins:
            online_feel = min(len(users) + 12, 48)
    except Exception:
        online_feel = 24
    return {
        "online_players_feel": online_feel,
        "mn2_prizes_today": round(mn2_prizes_today, 4),
        "bets_today_sample": bets_today,
    }


def _user_state(user_id: str) -> Dict[str, Any]:
    from backend.services import casino_service

    uid = (user_id or "").strip() or "default_user"
    balance = casino_service.get_balance(uid)
    quests = casino_service.get_daily_quests(uid)
    streak_days = int(quests.get("streak_days") or 0)
    free_daily = quests.get("free_daily_bet") or {}
    level = 1
    xp = 0
    try:
        from backend.services.casino_progression_service import get_user_progression

        prog = get_user_progression(uid)
        if prog.get("success"):
            level = int(prog.get("level") or 1)
            xp = int(prog.get("xp") or 0)
    except Exception:
        pass
    bonuses = quests.get("bonuses") or []
    daily_claimable = any(
        bool(b.get("eligible")) and not bool(b.get("claimed"))
        for b in bonuses
        if isinstance(b, dict)
    )
    quest_claimable = any(
        bool(q.get("complete")) and not bool(q.get("claimed"))
        for q in (quests.get("quests") or [])
        if isinstance(q, dict)
    )
    return {
        "balance": {
            "coins": balance.get("balance"),
            "mn2": balance.get("mn2_balance"),
            "usd": balance.get("fiat_balance"),
            "bets_today": balance.get("bets_today"),
            "max_bets_per_day": balance.get("max_bets_per_day"),
        },
        "streak_days": streak_days,
        "streak_badge": streak_days >= 3,
        "level": level,
        "xp": xp,
        "free_daily_available": bool(free_daily.get("available")),
        "daily_bonus_claimable": daily_claimable or quest_claimable,
        "quests_summary": {
            "complete": sum(1 for q in (quests.get("quests") or []) if q.get("complete")),
            "total": len(quests.get("quests") or []),
            "streak_days": streak_days,
        },
    }


def _active_events(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = cfg.get("events") or []
    out: List[Dict[str, Any]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if ev.get("enabled") is False:
            continue
        out.append({
            "id": ev.get("id"),
            "title": ev.get("title"),
            "description": ev.get("description"),
            "cta_label": ev.get("cta_label"),
            "cta_href": ev.get("cta_href"),
            "cta_game": ev.get("cta_game"),
            "badge": ev.get("badge"),
            "accent": ev.get("accent"),
        })
    return out


def get_casino_hub(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Single payload for the casino super-experience frontend."""
    from backend.services import casino_service
    from backend.services.social_platform_fanout_service import get_platform_hub

    cfg = _load_hub_config()
    uid = (user_id or "").strip() or "default_user"

    jackpots = casino_service.get_jackpots()
    feed = casino_service.get_activity_feed(limit=8)
    tournaments = casino_service.list_tournaments(user_id=uid)
    social = get_platform_hub()
    live = _live_stats()

    jp_pools = (jackpots.get("pools") or {}) if jackpots.get("success") else {}
    hero_jackpot = None
    highlight = (cfg.get("jackpot_display") or {}).get("highlight_currency") or "mn2"
    if isinstance(jp_pools.get(highlight), dict):
        hero_jackpot = {
            "currency": highlight,
            "pool": jp_pools[highlight].get("pool"),
        }
    elif isinstance(jp_pools.get("coins"), dict):
        hero_jackpot = {"currency": "coins", "pool": jp_pools["coins"].get("pool")}

    running_tourney = None
    for t in (tournaments.get("tournaments") or []):
        if isinstance(t, dict) and t.get("status") == "running":
            running_tourney = {
                "id": t.get("id"),
                "name": t.get("name"),
                "currency": t.get("currency"),
                "prize_pool": t.get("prize_pool"),
                "entrants": t.get("entrants"),
                "end_at": t.get("end_at"),
            }
            break

    platforms = []
    for p in (social.get("platforms") or []):
        if not isinstance(p, dict):
            continue
        platforms.append({
            "id": p.get("id"),
            "label": p.get("label"),
            "status": p.get("status"),
            "rewards_mn2": p.get("rewards"),
            "links": p.get("links") or {},
            "features": p.get("features") or {},
        })

    discord_cfg = cfg.get("social_sidebar") or {}
    return {
        "success": True,
        "hero": {
            **(cfg.get("hero") or {}),
            "jackpot": hero_jackpot,
            "online_players_feel": live["online_players_feel"],
            "mn2_prizes_today": live["mn2_prizes_today"],
            "running_tournament": running_tourney,
        },
        "featured_games": cfg.get("featured_games") or [],
        "categories": cfg.get("categories") or [],
        "game_categories": cfg.get("game_categories") or {},
        "events": _active_events(cfg),
        "cross_links": cfg.get("cross_links") or [],
        "jackpots": jackpots,
        "recent_wins": feed.get("feed") or [],
        "tournaments": tournaments.get("tournaments") or [],
        "social_platforms": platforms,
        "social_sidebar": {
            "discord_deep_link": discord_cfg.get("discord_deep_link") or "/discord-play/",
            "discord_earn_preview_mn2": discord_cfg.get("discord_earn_preview_mn2", 50),
            "show_platform_hub": discord_cfg.get("show_platform_hub", True),
        },
        "daily_bonus": cfg.get("daily_bonus") or {},
        "user": _user_state(uid),
        "jackpot_display": cfg.get("jackpot_display") or {},
    }
