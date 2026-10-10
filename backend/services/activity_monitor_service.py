"""Activity monitor status — tiles for customers, Discord, news, and live events."""
from __future__ import annotations

from typing import Any, Dict, List


def _news_snapshot(limit: int = 8) -> tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    try:
        from backend.routes.platform_news_routes import _load_news

        items = _load_news()[: max(1, min(limit, 30))]
    except Exception:
        items = []
    by_channel: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        ch = (item.get("channel") or item.get("category") or "general").strip().lower()
        by_channel.setdefault(ch, []).append(item)
    return items, by_channel


def get_monitor_status(*, news_limit: int = 8, event_limit: int = 20) -> Dict[str, Any]:
    customers: Dict[str, Any] = {"total": 0, "active_today": 0, "with_mn2": 0}
    try:
        from backend.services.customer_aggregator_service import stats

        customers = stats()
    except Exception:
        pass

    discord: Dict[str, Any] = {"status": "unknown", "configured": False}
    try:
        from backend.services.discord_service import outbox_stats

        discord = outbox_stats(30)
    except Exception:
        pass

    news, news_by_channel = _news_snapshot(news_limit)

    customer_events: List[Dict[str, Any]] = []
    recent_events: List[Dict[str, Any]] = []
    try:
        from backend.services.activity_events_service import recent

        recent_events = recent(limit=event_limit)
        customer_events = [
            row for row in recent_events
            if (row.get("type") or "") in ("customer_new", "customer_active")
        ]
    except Exception:
        pass

    return {
        "success": True,
        "tiles": {
            "customers": {
                "total": int(customers.get("total") or 0),
                "active_today": int(customers.get("active_today") or 0),
                "with_mn2": int(customers.get("with_mn2") or 0),
            },
            "discord": discord,
            "news": {
                "count": len(news),
                "channels": sorted(news_by_channel.keys()),
            },
        },
        "news": news,
        "news_by_channel": news_by_channel,
        "recent_customer_events": customer_events[:10],
        "recent_events": recent_events[:event_limit],
        "stream": {
            "sse": "/api/activity/stream",
            "recent": "/api/activity/recent",
        },
    }
