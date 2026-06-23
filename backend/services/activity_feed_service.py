"""Aggregate recent platform activity for SSE / HUD."""
from __future__ import annotations

from typing import Any, Dict, List


def recent_activity(limit: int = 25) -> List[Dict[str, Any]]:
    safe = max(1, min(int(limit or 25), 100))
    events: List[Dict[str, Any]] = []

    try:
        from backend.services.casino_service import get_activity_feed
        feed = get_activity_feed(limit=min(safe, 20))
        for row in feed.get("feed") or []:
            events.append({
                "kind": "casino_win",
                "ts": row.get("created_at"),
                "user_id": row.get("user_id"),
                "text": f"{row.get('game', 'casino')} win {row.get('payout', 0)} {row.get('currency', 'coins')}",
                "payload": row,
            })
    except Exception:
        pass

    try:
        from backend.services.mn2_ledger import _load_entries
        entries = _load_entries()[-safe:]
        for row in reversed(entries):
            events.append({
                "kind": "mn2_ledger",
                "ts": row.get("created_at"),
                "user_id": row.get("user_id"),
                "text": f"{row.get('entry_type', 'mn2')} {row.get('amount', 0)} MN2",
                "payload": {
                    "entry_type": row.get("entry_type"),
                    "amount": row.get("amount"),
                },
            })
    except Exception:
        pass

    try:
        from backend.services.aggregator_mn2_service import get_public_stats
        stats = get_public_stats()
        if stats.get("success"):
            events.insert(0, {
                "kind": "aggregator_stats",
                "ts": None,
                "user_id": None,
                "text": f"Aggregator MN2 earned today: {stats.get('platform_earned_today_mn2', 0)}",
                "payload": stats,
            })
    except Exception:
        pass

    try:
        from backend.services.activity_events_service import recent as recent_events
        for row in recent_events(limit=safe, channel=None):
            events.append({
                "kind": row.get("type") or "activity_event",
                "ts": row.get("ts"),
                "user_id": row.get("user_id"),
                "text": row.get("text") or row.get("type"),
                "payload": row.get("payload") or {},
            })
    except Exception:
        pass

    events.sort(key=lambda e: str(e.get("ts") or ""), reverse=True)
    return events[:safe]
