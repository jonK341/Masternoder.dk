"""Battle → platform_news (channel=game) + Discord #game (M8 #56). Off-request; no custody."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")


def _iso_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _discord_game(embed: Dict[str, Any], message_id: str) -> None:
    try:
        from backend.services.discord_service import post_message
        post_message("game", {"embeds": [embed]}, message_id=message_id)
    except Exception:
        pass


def notify_quick_battle(
    user_id: str,
    result: str,
    *,
    points_delta: int = 0,
    streak: int = 0,
) -> Dict[str, Any]:
    """Publish notable battle outcomes to game news + Discord (wins and hot streaks)."""
    result = (result or "").strip().lower()
    if result not in ("win", "loss", "draw"):
        return {"success": False, "skipped": True}
    notable = result == "win" or streak >= 3
    if not notable:
        return {"success": True, "skipped": True, "reason": "not_notable"}

    title = "Battle victory" if result == "win" else f"Battle streak ×{streak}"
    summary = (
        f"Player {user_id[:12]}… {result} a quick battle ({points_delta:+d} pts)."
        if result == "win"
        else f"Player {user_id[:12]}… on a {streak}-match streak in the arena."
    )
    item_id = f"battle-quick-{user_id}-{_iso_day()}-{result}-{streak}"
    try:
        from backend.services.platform_news_publish import publish
        pub = publish(
            item_id=item_id[:120],
            title=title,
            summary=summary[:400],
            channel="game",
            href="/battle/",
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    _discord_game(
        {
            "title": title,
            "description": summary[:500],
            "url": f"{_BASE_URL}/battle/",
            "footer": {"text": "Rewards and ranks update on-site — not in Discord."},
        },
        message_id=item_id[:160],
    )
    return {"success": True, "published": pub.get("success", True)}


def notify_tournament_join(
    user_id: str,
    tournament_id: str,
    tournament_name: Optional[str] = None,
    participants: Optional[int] = None,
) -> Dict[str, Any]:
    """Tournament signup → game channel + Discord quest funnel."""
    name = (tournament_name or tournament_id or "Tournament").strip()
    part_txt = f" ({participants} joined)" if participants is not None else ""
    summary = f"{user_id[:12]}… joined {name}{part_txt}. Complete quests on-site for MN2 rewards."
    item_id = f"battle-join-{tournament_id}-{user_id}-{_iso_day()}"
    try:
        from backend.services.platform_news_publish import publish
        pub = publish(
            item_id=item_id[:120],
            title=f"Tournament signup: {name}",
            summary=summary[:400],
            channel="game",
            href="/battle/",
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    _discord_game(
        {
            "title": f"Joined {name}",
            "description": summary[:500],
            "url": f"{_BASE_URL}/battle/",
            "footer": {"text": "Discord Quest Bot links — claim rewards on masternoder.dk."},
        },
        message_id=item_id[:160],
    )
    return {"success": True, "published": pub.get("success", True)}
