"""
LLM stage memoization — cache AI planning outputs by prompt hash.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CACHE_DIR = os.path.join(_BASE, "data", "video_stage_cache")
_DEFAULT_TTL = 86400 * 7


def _key(stage: str, prompt: str, extra: str = "") -> str:
    raw = f"{stage}|{prompt.strip()}|{extra.strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _path(key: str) -> str:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    return os.path.join(_CACHE_DIR, f"{key}.json")


def get(stage: str, prompt: str, extra: str = "", ttl_sec: int = _DEFAULT_TTL) -> Optional[Any]:
    k = _key(stage, prompt, extra)
    p = _path(k)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            row = json.load(f)
        if time.time() - float(row.get("ts") or 0) > ttl_sec:
            return None
        return row.get("value")
    except Exception:
        return None


def put(stage: str, prompt: str, value: Any, extra: str = "") -> None:
    k = _key(stage, prompt, extra)
    try:
        with open(_path(k), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "stage": stage, "value": value}, f, ensure_ascii=False)
    except Exception:
        pass
