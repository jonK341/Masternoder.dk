"""Append-only shared activity event log for SSE monitor, Discord, and cron."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_PATH = os.path.join(_BASE, "logs", "activity_events.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit(
    event_type: str,
    *,
    user_id: Optional[str] = None,
    channel: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    text: Optional[str] = None,
) -> Dict[str, Any]:
    row = {
        "ts": _iso(),
        "type": (event_type or "event").strip(),
        "user_id": user_id,
        "channel": channel,
        "text": text,
        "payload": payload or {},
    }
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    with _LOCK:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
    return {"success": True, "event": row}


def recent(limit: int = 50, channel: Optional[str] = None) -> List[Dict[str, Any]]:
    safe = max(1, min(int(limit or 50), 200))
    if not os.path.isfile(_LOG_PATH):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if channel and row.get("channel") != channel:
                        continue
                    rows.append(row)
                except Exception:
                    continue
    except Exception:
        return []
    return list(reversed(rows[-safe:]))
