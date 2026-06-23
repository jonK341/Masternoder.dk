"""
Context snapshot cache — memoize assembled generator context per user + profile hash.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CACHE_DIR = os.path.join(_BASE, "data", "generator_context_cache")
_DEFAULT_TTL = 3600


def _hash(user_id: str, context: Dict[str, Any]) -> str:
    raw = f"{user_id}|{json.dumps(context, sort_keys=True, default=str)}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _path(key: str) -> str:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    return os.path.join(_CACHE_DIR, f"{key}.json")


def get(user_id: str, context: Dict[str, Any], ttl_sec: int = _DEFAULT_TTL) -> Optional[Any]:
    k = _hash(user_id, context)
    p = _path(k)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            row = json.load(f)
        if time.time() - float(row.get("ts") or 0) > ttl_sec:
            return None
        return row.get("snapshot")
    except Exception:
        return None


def put(user_id: str, context: Dict[str, Any], snapshot: Any, ttl_sec: int = _DEFAULT_TTL) -> str:
    k = _hash(user_id, context)
    try:
        with open(_path(k), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "user_id": user_id, "snapshot": snapshot, "ttl_sec": ttl_sec}, f)
    except Exception:
        pass
    return k


def invalidate_user(user_id: str) -> int:
    """Best-effort purge of cached snapshots for a user."""
    if not os.path.isdir(_CACHE_DIR):
        return 0
    removed = 0
    uid = str(user_id)
    for name in os.listdir(_CACHE_DIR):
        if not name.endswith(".json"):
            continue
        p = os.path.join(_CACHE_DIR, name)
        try:
            with open(p, "r", encoding="utf-8") as f:
                row = json.load(f)
            if str(row.get("user_id")) == uid:
                os.remove(p)
                removed += 1
        except Exception:
            pass
    return removed
