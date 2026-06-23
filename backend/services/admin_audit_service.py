"""Append-only admin/ops action audit log (Gate S)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG = os.path.join(_BASE, "logs", "admin_audit.jsonl")


def log_action(action: str, *, actor: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
    row = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "action": action,
        "actor": actor or "ops",
        "payload": payload or {},
    }
    os.makedirs(os.path.dirname(_LOG), exist_ok=True)
    with _LOCK:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
