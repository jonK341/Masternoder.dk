#!/usr/bin/env python3
"""Generate data/casino_upgrades.json — 250 casino level-up upgrades."""
from __future__ import annotations

import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUT = os.path.join(_ROOT, "data", "casino_upgrades.json")

_CATEGORIES = [
    {
        "id": "slots",
        "name": "Slots",
        "icon": "🎰",
        "prefix": "Slot",
        "effects": [
            "reel_skin", "spin_animation", "symbol_glow", "payline_highlight", "jackpot_frame",
        ],
        "icons": ["🎰", "🍒", "7️⃣", "💎", "⭐", "🔔", "🃏", "🌟", "💫", "🎲"],
    },
    {
        "id": "table_games",
        "name": "Table Games",
        "icon": "🃏",
        "prefix": "Table",
        "effects": [
            "felt_skin", "chip_style", "card_back", "dealer_flair", "table_lighting",
        ],
        "icons": ["🃏", "♠️", "♥️", "♦️", "♣️", "🎴", "🟢", "🔴", "🎲", "🪙"],
    },
    {
        "id": "rewards",
        "name": "Rewards",
        "icon": "🎁",
        "prefix": "Reward",
        "effects": [
            "unlock_bonus_coins", "daily_bonus_boost", "quest_reward_flair", "level_up_fanfare",
            "coin_rain_fx",
        ],
        "icons": ["🎁", "💰", "🪙", "🏅", "✨", "🎉", "💵", "🤑", "💸", "🌈"],
    },
    {
        "id": "vip",
        "name": "VIP",
        "icon": "👑",
        "prefix": "VIP",
        "effects": [
            "vip_badge", "lounge_theme", "host_greeting", "priority_queue_cosmetic", "vip_frame",
        ],
        "icons": ["👑", "💎", "🥇", "🌟", "✨", "🏆", "🎖️", "💫", "🔱", "👸"],
    },
    {
        "id": "social",
        "name": "Social",
        "icon": "👥",
        "prefix": "Social",
        "effects": [
            "share_template", "crew_flair", "chat_emote", "friend_highlight", "big_win_poster",
        ],
        "icons": ["👥", "💬", "📣", "🤝", "❤️", "🔥", "📸", "🎬", "🌐", "📢"],
    },
    {
        "id": "mn2_economy",
        "name": "MN2 Economy",
        "icon": "🪙",
        "prefix": "MN2",
        "effects": [
            "wallet_skin", "deposit_highlight", "exchange_bridge_badge", "mn2_stake_flair",
            "treasury_ticker",
        ],
        "icons": ["🪙", "💱", "🔗", "⛓️", "🏦", "📊", "💹", "🔐", "🌉", "⚡"],
    },
    {
        "id": "visuals",
        "name": "Visuals",
        "icon": "🎨",
        "prefix": "Visual",
        "effects": [
            "ui_theme", "particle_pack", "banner_skin", "ambient_glow", "neon_accent",
        ],
        "icons": ["🎨", "🖌️", "🌈", "✨", "💜", "💙", "💚", "🧡", "🩷", "🌙"],
    },
    {
        "id": "jackpots",
        "name": "Jackpots",
        "icon": "💰",
        "prefix": "Jackpot",
        "effects": [
            "ticker_skin", "pool_glow", "win_celebration", "jackpot_badge", "mega_win_fx",
        ],
        "icons": ["💰", "💎", "🏆", "🎰", "💥", "🎆", "🎇", "✨", "🌟", "👑"],
    },
    {
        "id": "streaks",
        "name": "Streaks",
        "icon": "🔥",
        "prefix": "Streak",
        "effects": [
            "streak_badge", "streak_shield_cosmetic", "hot_streak_fx", "win_streak_banner",
            "daily_streak_tracker",
        ],
        "icons": ["🔥", "⚡", "💪", "🚀", "📈", "🎯", "🏃", "⭐", "💫", "🌋"],
    },
    {
        "id": "missions",
        "name": "Missions",
        "icon": "📋",
        "prefix": "Mission",
        "effects": [
            "quest_tracker_skin", "mission_slot", "weekly_board_flair", "achievement_pin",
            "progress_bar_theme",
        ],
        "icons": ["📋", "✅", "🎯", "📝", "🗺️", "🧭", "🏁", "📌", "🔖", "🎖️"],
    },
]

_TIER_LEVELS = [1, 2, 4, 6, 10]
_TIER_NAMES = ["Bronze", "Silver", "Gold", "Platinum", "Diamond"]


def _tier_for_index(i: int) -> int:
    return min(4, i // 5)


def _cost_for(tier: int, sub: int, cat_id: str) -> dict:
    base = 100 + tier * tier * 120 + sub * 40
    out: dict = {"cost_coins": base}
    if tier >= 3:
        out["cost_xp"] = 200 + tier * 150 + sub * 25
    # MN2 rail must match coins_per_mn2 (data/mn2_config.json) — never a flat micro fee.
    if tier >= 4 and sub >= 2:
        coins_per_mn2 = 100.0
        try:
            cfg_path = os.path.join(_ROOT, "data", "mn2_config.json")
            with open(cfg_path, encoding="utf-8") as fh:
                coins_per_mn2 = float(json.load(fh).get("coins_per_mn2") or 100)
        except Exception:
            pass
        out["cost_mn2"] = round(base / max(coins_per_mn2, 1.0), 4)
    return out


def _bonus_for(effect: str, tier: int) -> dict:
    bonuses: dict = {"cosmetic_only": True}
    if effect == "unlock_bonus_coins":
        bonuses["bonus_coins_on_unlock"] = 25 + tier * 50
    elif effect in ("daily_bonus_boost", "quest_reward_flair"):
        bonuses["xp_boost_pct"] = 2 + tier * 3
    elif effect == "level_up_fanfare":
        bonuses["level_up_flair"] = True
    elif effect == "vip_badge":
        bonuses["vip_flair_tier"] = tier + 1
    elif effect == "streak_shield_cosmetic":
        bonuses["streak_shield_cosmetic"] = True
    elif effect == "mission_slot":
        bonuses["mission_tracker_slots"] = 1 + tier
    else:
        bonuses["visual_effect"] = effect
    return bonuses


def build_catalog() -> dict:
    upgrades = []
    for cat in _CATEGORIES:
        cat_id = cat["id"]
        effects = cat["effects"]
        icons = cat["icons"]
        for i in range(25):
            tier = _tier_for_index(i)
            sub = i % 5
            tier_name = _TIER_NAMES[tier]
            effect = effects[sub % len(effects)]
            uid = f"cu-{cat_id}-{i + 1:02d}"
            name = f"{cat['prefix']} {tier_name} {sub + 1}"
            desc = (
                f"{cat['name']} upgrade tier {tier + 1} — "
                f"{effect.replace('_', ' ')} (cosmetic, no RTP change)."
            )
            row = {
                "id": uid,
                "name": name,
                "description": desc,
                "category": cat_id,
                "category_name": cat["name"],
                "tier": tier + 1,
                "level_required": _TIER_LEVELS[tier],
                "icon": icons[i % len(icons)],
                "effect": effect,
                **_cost_for(tier, sub, cat_id),
                **_bonus_for(effect, tier),
            }
            if i > 0 and sub > 0:
                row["prerequisite"] = f"cu-{cat_id}-{i:02d}"
            upgrades.append(row)

    assert len(upgrades) == 250, f"expected 250 upgrades, got {len(upgrades)}"
    return {
        "version": 1,
        "total": 250,
        "categories": [
            {"id": c["id"], "name": c["name"], "icon": c["icon"], "count": 25}
            for c in _CATEGORIES
        ],
        "upgrades": upgrades,
    }


def main() -> None:
    catalog = build_catalog()
    os.makedirs(os.path.dirname(_OUT), exist_ok=True)
    with open(_OUT, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"Wrote {catalog['total']} upgrades to {_OUT}")


if __name__ == "__main__":
    main()
