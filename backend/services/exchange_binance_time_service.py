"""Binance signed-request clock sync (fixes API -1021 recvWindow errors)."""
from __future__ import annotations

import threading
import time
from typing import Any, Dict

_lock = threading.Lock()
_offset_ms = 0.0
_last_sync_mono = 0.0
_RECV_WINDOW_MS = 10_000


def recv_window_ms() -> int:
    return _RECV_WINDOW_MS


def binance_timestamp_ms(*, force_sync: bool = False) -> int:
    """Local clock adjusted to Binance server time."""
    global _last_sync_mono
    now_mono = time.monotonic()
    if force_sync or (now_mono - _last_sync_mono) > 300:
        sync_binance_time()
    with _lock:
        return int(time.time() * 1000 + _offset_ms)


def sync_binance_time() -> Dict[str, Any]:
    """Fetch GET /api/v3/time and store offset (server - local)."""
    global _offset_ms, _last_sync_mono
    try:
        import requests
    except Exception as exc:
        return {"success": False, "error": f"requests_unavailable: {exc}"}

    try:
        resp = requests.get("https://api.binance.com/api/v3/time", timeout=5)
        body = resp.json() if resp.status_code == 200 else {}
        server_ms = float(body.get("serverTime") or 0)
        if server_ms <= 0:
            return {"success": False, "error": "no_server_time", "status_code": resp.status_code}
        local_ms = time.time() * 1000
        with _lock:
            _offset_ms = server_ms - local_ms
            _last_sync_mono = time.monotonic()
            offset = _offset_ms
        return {
            "success": True,
            "offset_ms": round(offset, 1),
            "offset_sec": round(offset / 1000.0, 3),
            "clock_ok": abs(offset) < 3000,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def clock_status() -> Dict[str, Any]:
    """Quick health check for daemon preflight."""
    sync = sync_binance_time()
    return {
        "success": bool(sync.get("success")),
        "clock_ok": bool(sync.get("clock_ok")),
        "offset_ms": sync.get("offset_ms"),
        "offset_sec": sync.get("offset_sec"),
        "error": sync.get("error"),
    }
