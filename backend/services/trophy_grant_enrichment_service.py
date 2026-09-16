"""Post-grant enrichment: per-edition AI GIF, anchor priority, auction, badges, Discord."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "trophy_grant_enrichment_config.json")


def get_config() -> Dict[str, Any]:
    defaults = {
        "enabled": True,
        "per_edition_gif": True,
        "anchor_priority_staking": 100,
        "anchor_priority_block_mint": 50,
        "auto_auction_staking_wins": True,
        "auto_auction_floor_usd": 4.99,
        "discord_staking_wins": True,
        "profile_badge_staking_champion": True,
        "team_pool_notify": True,
        "streak_bonus_enabled": True,
        "streak_min_days": 3,
        "streak_combat_bonus": 5,
        "battle_ready_notification": True,
    }
    if not os.path.isfile(_CONFIG_PATH):
        return defaults
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        defaults.update(raw if isinstance(raw, dict) else {})
    except Exception:
        pass
    return defaults


def _apply_streak_bonus(user_id: str, battle_stats: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not cfg.get("streak_bonus_enabled", True):
        return battle_stats
    try:
        from backend.services.mn2_staking_service import get_stake

        stake = get_stake(user_id) or {}
        streak_days = int(stake.get("streak_days") or 0)
        min_days = int(cfg.get("streak_min_days") or 3)
        if streak_days < min_days:
            return battle_stats
        bonus = int(cfg.get("streak_combat_bonus") or 5)
        out = dict(battle_stats)
        out["combat_rating"] = int(out.get("combat_rating") or 0) + bonus
        out["streak_bonus"] = bonus
        out["streak_days"] = streak_days
        return out
    except Exception:
        return battle_stats


def _boost_anchor_priority(edition_key: str, priority: int) -> Dict[str, Any]:
    try:
        from backend.services.trophy_anchor_service import set_anchor_job_priority

        return set_anchor_job_priority(edition_key, priority)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _auto_list_auction(
    user_id: str,
    item_id: str,
    edition_no: int,
    floor_usd: float,
) -> Dict[str, Any]:
    try:
        from backend.services.shop_auction_service import create_listing
        from backend.services.trophy_pricing_service import get_effective_price

        pricing = get_effective_price(item_id)
        price_coins = int(pricing.get("effective_price_coins") or 0)
        if price_coins <= 0:
            price_coins = max(100, int(float(floor_usd) * 100))
        return create_listing(user_id, item_id, 1, price_coins, edition_no=int(edition_no))
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _update_profile_badge(user_id: str, acquired_via: str) -> Dict[str, Any]:
    if acquired_via != "staking_winner":
        return {"skipped": True}
    try:
        from backend.services.user_onboarding import user_onboarding

        profile = user_onboarding.get_user_profile(user_id) or {}
        prefs = profile.get("preferences") or {}
        if isinstance(prefs, str):
            prefs = json.loads(prefs) if prefs else {}
        badges = prefs.get("trophy_badges") or {}
        badges["staking_champion"] = True
        badges["staking_wins"] = int(badges.get("staking_wins") or 0) + 1
        badges["profile_label"] = "Interval champion"
        prefs["trophy_badges"] = badges
        return user_onboarding.update_user_profile(user_id, {"preferences": prefs})
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _notify_team_pool(user_id: str, grant: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from backend.services.mn2_staking_teams import get_team_for_user
        from backend.services.user_engagement import add_notification

        team = get_team_for_user(user_id)
        if not team or not team.get("team_id"):
            return {"skipped": True, "reason": "no_team"}
        members = team.get("members") or []
        notified = 0
        for member in members:
            mid = (member.get("user_id") or member) if isinstance(member, dict) else str(member)
            if not mid or mid == user_id:
                continue
            add_notification(
                mid,
                "Team staking trophy",
                f"Teammate won block trophy #{grant.get('block_height')} — your pool multiplier helped.",
                category="staking_trophy_team",
                metadata={"team_id": team.get("team_id"), "winner": user_id, **grant},
            )
            notified += 1
        return {"success": True, "notified": notified}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def enrich_block_trophy_grant(
    user_id: str,
    item_id: str,
    edition_no: int,
    edition_key: str,
    proof_hash: str,
    block_height: int,
    *,
    acquired_via: str = "block_mint",
    battle_stats: Optional[Dict[str, Any]] = None,
    license_number: str = "",
    trading_profile: Optional[Dict[str, Any]] = None,
    interval_id: str = "",
    reward_mn2: float = 0.0,
) -> Dict[str, Any]:
    """Run all post-grant enrichments for a block trophy edition."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": True, "skipped": True, "reason": "disabled"}

    uid = (user_id or "").strip()
    stats = dict(battle_stats or {})
    stats = _apply_streak_bonus(uid, stats, cfg)
    result: Dict[str, Any] = {"success": True, "edition_key": edition_key, "steps": {}}

    gif_url: Optional[str] = None
    image_url: Optional[str] = None
    if cfg.get("per_edition_gif", True):
        try:
            from backend.services.block_trophy_media_service import ensure_edition_media
            from backend.services.trophy_fulfillment_service import patch_edition_fields

            media = ensure_edition_media(
                edition_key,
                int(block_height),
                battle_stats=stats,
                license_number=license_number,
                edition_no=int(edition_no or 1),
            )
            result["steps"]["per_edition_gif"] = media
            if media.get("success"):
                gif_url = media.get("gif_url")
                image_url = media.get("image_url")
                patch_fields: Dict[str, Any] = {
                    "gif_url": gif_url,
                    "image_url": image_url,
                    "edition_gif_url": gif_url,
                    "per_edition_media": True,
                    "ai_generated": True,
                }
                if stats:
                    patch_fields["battle_stats"] = stats
                patch_edition_fields(uid, item_id, int(edition_no or 1), patch_fields)
        except Exception as exc:
            result["steps"]["per_edition_gif"] = {"success": False, "error": str(exc)}

    priority = int(cfg.get("anchor_priority_default") or 0)
    if acquired_via == "staking_winner":
        priority = int(cfg.get("anchor_priority_staking") or 100)
    elif acquired_via == "block_mint":
        priority = int(cfg.get("anchor_priority_block_mint") or 50)
    result["steps"]["anchor_priority"] = _boost_anchor_priority(edition_key, priority)

    listing = None
    if acquired_via == "staking_winner" and cfg.get("auto_auction_staking_wins", True):
        listing = _auto_list_auction(
            uid,
            item_id,
            int(edition_no or 1),
            float(cfg.get("auto_auction_floor_usd") or 4.99),
        )
        result["steps"]["auto_auction"] = listing

    if cfg.get("profile_badge_staking_champion", True):
        result["steps"]["profile_badge"] = _update_profile_badge(uid, acquired_via)

    if cfg.get("team_pool_notify", True) and acquired_via == "staking_winner":
        grant_ctx = {
            "user_id": uid,
            "block_height": block_height,
            "edition_key": edition_key,
            "license_number": license_number,
            "acquired_via": acquired_via,
            "gif_url": gif_url,
            "battle_stats": stats,
        }
        result["steps"]["team_pool"] = _notify_team_pool(uid, grant_ctx)

    grant_payload = {
        "user_id": uid,
        "item_id": item_id,
        "edition_no": edition_no,
        "edition_key": edition_key,
        "block_height": block_height,
        "license_number": license_number,
        "acquired_via": acquired_via,
        "gif_url": gif_url,
        "edition_gif_url": gif_url,
        "image_url": image_url,
        "battle_stats": stats,
        "interval_id": interval_id,
        "reward_mn2": reward_mn2,
        "auction_listing_id": (listing or {}).get("listing_id") if isinstance(listing, dict) else None,
    }

    if cfg.get("discord_staking_wins", True) and acquired_via == "staking_winner":
        try:
            from backend.services.trophy_discord_fanout import post_trophy_grant

            result["steps"]["discord"] = post_trophy_grant(grant_payload)
        except Exception as exc:
            result["steps"]["discord"] = {"success": False, "error": str(exc)}

    if cfg.get("battle_ready_notification", True):
        try:
            if acquired_via == "staking_winner":
                from backend.services.mn2_staking_notifications import on_staking_trophy_grant_battle_ready

                on_staking_trophy_grant_battle_ready(uid, grant_payload)
            else:
                from backend.services.mn2_staking_notifications import on_block_trophy_grant_battle_ready

                on_block_trophy_grant_battle_ready(uid, grant_payload)
        except Exception as exc:
            result["steps"]["battle_notification"] = {"success": False, "error": str(exc)}

    result["gif_url"] = gif_url
    result["image_url"] = image_url
    result["battle_stats"] = stats
    return result
