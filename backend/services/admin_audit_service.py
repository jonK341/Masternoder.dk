"""Append-only admin action audit log (Gate S)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG = os.path.join(_BASE, "logs", "admin_audit.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log_action(
    action: str,
    *,
    actor: str = "system",
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append one admin/ops action to the audit log."""
    row = {
        "ts": _iso(),
        "action": (action or "unknown").strip(),
        "actor": (actor or "system").strip(),
        "payload": payload or {},
    }
    os.makedirs(os.path.dirname(_LOG), exist_ok=True)
    with _LOCK:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
    return {"success": True, "entry": row}


def recent(limit: int = 50, action_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read recent audit entries (newest last in file; returned newest-first)."""
    safe = max(1, min(int(limit or 50), 500))
    if not os.path.isfile(_LOG):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if action_prefix and not str(row.get("action") or "").startswith(action_prefix):
                        continue
                    rows.append(row)
                except Exception:
                    continue
    except Exception:
        return []
    return list(reversed(rows[-safe:]))
