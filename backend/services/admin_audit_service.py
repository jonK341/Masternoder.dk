"""
Admin / ops audit log (Gate S).

Append-only JSONL of privileged actions (treasury, control board, scanner events).
Request routes and scanners call `log_action`; never blocks money paths on failure.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG = os.path.join(_BASE, "logs", "admin_audit.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log_action(
    action: str,
    actor: str = "ops",
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append one audit row. Never raises to callers — returns success flag."""
    row = {
        "ts": _iso(),
        "action": str(action or "").strip() or "unknown",
        "actor": str(actor or "ops").strip() or "ops",
        "payload": payload if isinstance(payload, dict) else {},
    }
    try:
        path = _LOG
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        line = json.dumps(row, default=str) + "\n"
        with _LOCK:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
        return {"success": True, "action": row["action"]}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
