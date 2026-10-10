"""Short-lived response cache with a bounded wait and background fill.

The first caller starts the work. Later callers wait up to ``timeout`` seconds
and otherwise receive the last payload or a fallback so a slow upstream cannot
hold the request open.
"""
from __future__ import annotations

import threading
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

from flask import current_app, jsonify, request

_LOCK = threading.Lock()
_STORE: Dict[str, Tuple[float, Any]] = {}
_EVENTS: Dict[str, threading.Event] = {}
_RUNNING: Dict[str, bool] = {}
_MAX_KEYS = 512


def clear_cache() -> None:
    with _LOCK:
        _STORE.clear()
        _EVENTS.clear()
        _RUNNING.clear()


def _fresh(key: str, ttl: float, now: float) -> Any:
    hit = _STORE.get(key)
    if not hit:
        return None
    if now - hit[0] > ttl:
        return None
    return hit[1]


def remember(
    key: str,
    ttl: float,
    builder: Callable[[], Any],
    *,
    timeout: float = 3.0,
    fallback: Optional[dict] = None,
) -> Any:
    """Return a cached value, or start ``builder`` and wait at most ``timeout``."""
    now = time.monotonic()
    with _LOCK:
        cached = _fresh(key, ttl, now)
        if cached is not None:
            if isinstance(cached, dict):
                out = dict(cached)
                out["cached"] = True
                return out
            return cached
        event = _EVENTS.get(key)
        running = _RUNNING.get(key, False)
        if event is None or not running:
            event = threading.Event()
            _EVENTS[key] = event
            _RUNNING[key] = True
            start_worker = True
        else:
            start_worker = False
        stale = _STORE.get(key)

    if start_worker:
        def _run():
            try:
                value = builder()
                with _LOCK:
                    if len(_STORE) >= _MAX_KEYS:
                        _STORE.clear()
                    _STORE[key] = (time.monotonic(), value)
            finally:
                with _LOCK:
                    _RUNNING[key] = False
                    done = _EVENTS.get(key)
                if done is not None:
                    done.set()

        threading.Thread(target=_run, name="bounded-cache", daemon=True).start()

    if event.wait(timeout):
        with _LOCK:
            hit = _STORE.get(key)
        if hit is not None:
            value = hit[1]
            if isinstance(value, dict):
                out = dict(value)
                out.setdefault("cached", False)
                return out
            return value

    if stale is not None:
        value = stale[1]
        if isinstance(value, dict):
            out = dict(value)
            out["stale"] = True
            out["cached"] = True
            return out
        return value

    body = dict(fallback or {"success": False, "error": "timeout", "pending": True})
    body.setdefault("pending", True)
    return body


def cached_get(ttl: float = 20.0, timeout: float = 3.0, fallback: Optional[dict] = None):
    """Cache a GET view. The view runs in a copied request context."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if request.method != "GET":
                return view(*args, **kwargs)
            app = current_app._get_current_object()
            environ = request.environ.copy()
            view_args = args
            view_kwargs = dict(kwargs)
            key = f"{view.__module__}:{view.__name__}:{request.full_path}"

            def builder():
                with app.request_context(environ):
                    result = view(*view_args, **view_kwargs)
                status = 200
                response = result
                if isinstance(result, tuple):
                    response = result[0]
                    status = int(result[1]) if len(result) > 1 else 200
                data = response.get_json(silent=True) if hasattr(response, "get_json") else response
                if not isinstance(data, dict):
                    data = {"success": True, "payload": data}
                return {"data": data, "status": status}

            packed = remember(key, ttl, builder, timeout=timeout, fallback={
                "data": dict(fallback or {"success": False, "error": "timeout", "pending": True}),
                "status": 200,
            })
            data = packed.get("data") if isinstance(packed, dict) else packed
            status = int(packed.get("status") or 200) if isinstance(packed, dict) else 200
            if isinstance(data, dict) and packed.get("cached"):
                data = dict(data)
                data["cached"] = True
            if isinstance(data, dict) and packed.get("stale"):
                data = dict(data)
                data["stale"] = True
            if isinstance(data, dict) and packed.get("pending") and "pending" not in data:
                data = dict(data)
                data["pending"] = True
            return jsonify(data), status

        return wrapper

    return decorator
