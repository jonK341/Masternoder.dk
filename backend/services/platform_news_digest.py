"""Daily platform news digest for Discord M8 #55."""
from __future__ import annotations

from typing import Any, Dict


def run_daily_digest() -> Dict[str, Any]:
    from backend.routes.platform_news_routes import _load_news
    from backend.services.discord_service import post_message

    items = _load_news()[:5]
    lines = [f"**{i.get('title', 'News')}** — {i.get('summary', '')[:120]}" for i in items]
    payload = {
        "embeds": [{
            "title": "MasterNoder Daily Digest",
            "description": "\n".join(lines) or "No news today.",
            "footer": {"text": "Affiliate/partner links may apply. Not gambling solicitation."},
        }],
    }
    result = post_message("announcements", payload, message_id=f"digest:{items[0].get('id') if items else 'empty'}")
    return {"success": result.get("success"), "items": len(items), "discord": result}
