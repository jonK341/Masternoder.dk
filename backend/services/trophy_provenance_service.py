"""Global provenance chain for trophy editions (plan 003 A-U3 + marketplace polish)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_PATH = os.path.join(_BASE, "data", "trophy_provenance.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_event(
    edition_key: str,
    event_type: str,
    *,
    user_id: str = "",
    from_user_id: str = "",
    to_user_id: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ekey = (edition_key or "").strip()
    if not ekey:
        return {"success": False, "error": "missing_edition_key"}
    row = {
        "edition_key": ekey,
        "event_type": (event_type or "unknown").strip(),
        "user_id": (user_id or "").strip(),
        "from_user_id": (from_user_id or "").strip(),
        "to_user_id": (to_user_id or "").strip(),
        "at": _iso(),
        "metadata": metadata or {},
    }
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    with _LOCK:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    return {"success": True, "event": row}


def get_chain(edition_key: str, *, limit: int = 50) -> Dict[str, Any]:
    ekey = (edition_key or "").strip()
    rows: List[Dict[str, Any]] = []
    if os.path.isfile(_LOG_PATH):
        try:
            with open(_LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("edition_key") == ekey:
                        rows.append(row)
        except Exception:
            pass
    rows.sort(key=lambda r: r.get("at") or "")
    rows = rows[-max(1, min(limit, 200)) :]
    return {"success": True, "edition_key": ekey, "events": rows, "count": len(rows)}
