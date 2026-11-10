"""Tiny Redis bus for exchange mid/order state, with a JSON file fallback.

When Redis is down (or ``EXCHANGE_REDIS_URL`` is empty and no local server
answers), every get/set lands under ``data/crypto_exchange/bus/``.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_fast_json import dumps as _json_dumps
from backend.services.exchange_fast_json import try_loads as _json_try_loads

PREFIX = "mn:xchg:"
_FALLBACK_DIR = os.path.join(ex._BASE, "data", "crypto_exchange", "bus")
_client = None
_client_failed = False


def redis_url() -> str:
    return (os.environ.get("EXCHANGE_REDIS_URL") or "redis://127.0.0.1:6379/0").strip()


def _fallback_path(key: str) -> str:
    safe = key.replace(":", "__").replace("/", "_")
    return os.path.join(_FALLBACK_DIR, f"{safe}.json")


def get_client():
    """Lazy Redis client. Returns None when Redis is unavailable."""
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed or not redis_url():
        return None
    try:
        import redis
    except Exception:
        _client_failed = True
        return None
    try:
        client = redis.Redis.from_url(redis_url(), socket_connect_timeout=0.4, socket_timeout=0.8)
        client.ping()
        _client = client
        return _client
    except Exception:
        _client_failed = True
        return None


def reset_client() -> None:
    """Drop the cached client (tests and reconnect after Redis comes up)."""
    global _client, _client_failed
    _client = None
    _client_failed = False


def bus_set(key: str, value: Any, *, ttl_sec: Optional[float] = None) -> str:
    payload = {"ts": time.time(), "value": value}
    raw = _json_dumps(payload)
    client = get_client()
    full = PREFIX + key
    if client is not None:
        try:
            if ttl_sec and ttl_sec > 0:
                client.setex(full, int(ttl_sec), raw)
            else:
                client.set(full, raw)
            return "redis"
        except Exception:
            reset_client()
    os.makedirs(_FALLBACK_DIR, exist_ok=True)
    with open(_fallback_path(key), "w", encoding="utf-8") as handle:
        handle.write(raw + "\n")
    return "file"


def bus_get(key: str, *, max_age_sec: Optional[float] = None) -> Optional[Any]:
    client = get_client()
    full = PREFIX + key
    raw = None
    if client is not None:
        try:
            blob = client.get(full)
            raw = blob.decode("utf-8") if isinstance(blob, (bytes, bytearray)) else blob
        except Exception:
            reset_client()
            raw = None
    if raw is None:
        path = _fallback_path(key)
        if not os.path.exists(path):
            return None
        try:
            raw = open(path, encoding="utf-8").read()
        except Exception:
            return None
    payload = _json_try_loads(raw)
    if not isinstance(payload, dict) or "value" not in payload:
        return None
    if max_age_sec is not None:
        try:
            age = time.time() - float(payload.get("ts") or 0)
        except (TypeError, ValueError):
            return None
        if age > max_age_sec:
            return None
    return payload["value"]


def bus_get_meta(key: str) -> Optional[Dict[str, Any]]:
    """Return ``{ts, value, backend}`` without the age filter."""
    client = get_client()
    full = PREFIX + key
    backend = "redis"
    raw = None
    if client is not None:
        try:
            blob = client.get(full)
            raw = blob.decode("utf-8") if isinstance(blob, (bytes, bytearray)) else blob
        except Exception:
            reset_client()
            raw = None
    if raw is None:
        backend = "file"
        path = _fallback_path(key)
        if not os.path.exists(path):
            return None
        try:
            raw = open(path, encoding="utf-8").read()
        except Exception:
            return None
    payload = _json_try_loads(raw)
    if not isinstance(payload, dict) or "value" not in payload:
        return None
    return {"ts": float(payload.get("ts") or 0), "value": payload["value"], "backend": backend}


def backend_name() -> str:
    return "redis" if get_client() is not None else "file"
