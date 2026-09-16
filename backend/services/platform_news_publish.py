"""Publish platform news items with channel support (Phase 5)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_NEWS = os.path.join(_BASE, "data", "platform_news.json")


def publish(
    *,
    item_id: str,
    title: str,
    summary: str,
    channel: str,
    href: str = "/",
    featured: bool = False,
) -> Dict[str, Any]:
    row = {
        "id": item_id,
        "title": title,
        "summary": summary,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "category": channel,
        "channel": channel,
        "href": href,
        "featured": featured,
    }
    try:
        with _LOCK:
            data = {"items": []}
            if os.path.isfile(_NEWS):
                try:
                    with open(_NEWS, "r", encoding="utf-8") as f:
                        data = json.load(f) or {"items": []}
                except Exception:
                    pass
            items = data.get("items") if isinstance(data.get("items"), list) else []
            items = [i for i in items if i.get("id") != item_id]
            items.insert(0, row)
            data["items"] = items[:200]
            os.makedirs(os.path.dirname(_NEWS), exist_ok=True)
            tmp = _NEWS + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, _NEWS)
    except Exception as exc:
        return {"success": False, "error": f"platform_news_write_failed: {exc}"}
    try:
        from backend.services.activity_events_service import emit
        emit("platform_news", channel=channel, text=title, payload=row)
    except Exception:
        pass
    return {"success": True, "item": row}
