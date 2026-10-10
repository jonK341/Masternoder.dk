"""Profit daemon — periodic maintenance (payout config, logs, health probe)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.profit_daemon_paths import heartbeat_path

_DEFAULT_INTERVAL_SEC = 300


def background_ops_interval_sec() -> int:
    try:
        iv = int(os.environ.get("PROFIT_DAEMON_BACKGROUND_OPS_INTERVAL", str(_DEFAULT_INTERVAL_SEC)))
    except (TypeError, ValueError):
        iv = _DEFAULT_INTERVAL_SEC
    return max(60, iv)


def background_ops_enabled() -> bool:
    raw = os.environ.get("PROFIT_DAEMON_BACKGROUND_OPS", "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def profit_daemon_health_probe(*, alert_on_stale: bool = False) -> Dict[str, Any]:
    """Lightweight heartbeat age for uwsgi /api/health/system (no full monitor_status)."""
    path = heartbeat_path()
    hb = ex._read_json(path, {})
    updated = str(hb.get("updated_at") or "")
    stale_sec = float(os.environ.get("PROFIT_DAEMON_STALE_SEC", "420"))
    age: Optional[float] = None
    if updated:
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            age = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds())
        except Exception:
            age = None
    if age is None:
        status = "unknown"
    elif age <= stale_sec:
        status = "healthy"
    else:
        status = "offline"
    out: Dict[str, Any] = {
        "success": status in ("healthy", "unknown"),
        "status": status,
        "heartbeat_path": path,
        "updated_at": updated or None,
        "age_sec": round(age, 1) if age is not None else None,
        "stale_threshold_sec": stale_sec,
        "profile": hb.get("profile"),
        "mode": hb.get("mode"),
    }
    if alert_on_stale and status == "offline":
        try:
            from backend.services.profit_daemon_ops_service import maybe_alert_heartbeat_stale

            out["stale_alert"] = maybe_alert_heartbeat_stale(max_age_sec=stale_sec)
        except Exception as exc:
            out["stale_alert"] = {"success": False, "error": str(exc)}
    return out


def run_background_ops_tick(threads: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Maintenance tick — payout env sync, log rotation, worker telemetry."""
    if not background_ops_enabled():
        return {"success": True, "skipped": True, "reason": "disabled"}
    out: Dict[str, Any] = {"success": True}
    try:
        from backend.services.exchange_payout_service import sync_auto_sweep_from_env

        out["payout_sync"] = sync_auto_sweep_from_env()
    except Exception as exc:
        out["payout_sync"] = {"success": False, "error": str(exc)}
    try:
        from backend.services.profit_daemon_ops_service import rotate_daemon_logs

        out["log_rotate"] = rotate_daemon_logs()
    except Exception as exc:
        out["log_rotate"] = {"success": False, "error": str(exc)}
    if threads:
        try:
            from backend.services.profit_daemon_ops_service import worker_thread_health

            out["workers"] = worker_thread_health(threads)
        except Exception as exc:
            out["workers"] = {"success": False, "error": str(exc)}
    out["health"] = profit_daemon_health_probe(alert_on_stale=False)
    return out
