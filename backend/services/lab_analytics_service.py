"""
Lab hub analytics — append-only event log for research, projects, roundtable, co-tech, milestones.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EVENTS_FILE = os.path.join(_PROJECT_ROOT, "data", "lab_analytics_events.json")
_MAX_EVENTS = 5000
_ALLOWED_TYPES = frozenset({
    "research",
    "project",
    "project_join",
    "roundtable",
    "co_tech",
    "v2_milestone",
    "explore",
    "deep_scan",
    "idea_pin",
    "project_brainstorm",
})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_events() -> Dict[str, Any]:
    try:
        with open(_EVENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("events"), list):
            return data
    except Exception:
        pass
    return {"version": 1, "events": []}


def _save_events(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_EVENTS_FILE), exist_ok=True)
    with open(_EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_lab_analytics(
    user_id: str,
    event_type: str,
    *,
    label: str = "",
    detail: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    et = (event_type or "").strip().lower()
    if et not in _ALLOWED_TYPES:
        return {"success": False, "error": "invalid_event_type"}
    uid = (user_id or "default_user").strip() or "default_user"
    entry = {
        "id": f"la_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "user_id": uid,
        "type": et,
        "label": (label or et)[:200],
        "detail": (detail or "")[:2000],
        "metadata": metadata if isinstance(metadata, dict) else {},
        "at": _now_iso(),
    }
    data = _load_events()
    events: List[Dict[str, Any]] = data.get("events") or []
    events.append(entry)
    data["events"] = events[-_MAX_EVENTS:]
    data["updated_at"] = entry["at"]
    try:
        _save_events(data)
    except Exception:
        return {"success": False, "error": "could_not_save"}
    try:
        from backend.services.unified_points_sync import unified_points_sync_device

        unified_points_sync_device.record_domain_sync("lab_analytics", count=1)
    except Exception:
        pass
    return {"success": True, "event": entry}


def list_lab_analytics(user_id: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    data = _load_events()
    events = data.get("events") or []
    if not isinstance(events, list):
        return []
    uid = (user_id or "").strip()
    rows = events
    if uid:
        rows = [e for e in events if isinstance(e, dict) and e.get("user_id") == uid]
    lim = max(1, min(int(limit or 50), 200))
    return list(reversed(rows[-lim:]))
