"""Profit daemon instance registry — who is running the daemon, and where.

The daemon stack can run on the server (systemd) or on the owner's laptop
(cmd launchers / laptop control app). Both trade against the same venue
accounts, so two live instances at once means duplicate orders and duplicate
PayPal sweeps ("double tick").

Every instance reports itself here (local file write on the server, or the
admin-key-gated /api/profit-daemon/heartbeat endpoint from a laptop). The
monitor exposes active instances and raises a conflict flag when more than
one instance is alive inside the stale window.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.services import crypto_exchange_service as ex

_INSTANCES_FILE = os.path.join(ex._DATA_DIR, "profit_daemon_instances.json")
_MAX_INSTANCES = 20


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _age_sec(ts: str) -> float | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None


def _stale_threshold_sec() -> float:
    return float(os.environ.get("PROFIT_DAEMON_STALE_SEC", "300"))


def _load() -> Dict[str, Any]:
    data = ex._read_json(_INSTANCES_FILE, {})
    return data if isinstance(data, dict) else {}


def report_instance(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert one daemon instance. Called on every heartbeat."""
    instance_id = str(payload.get("instance_id") or "").strip()
    if not instance_id:
        return {"success": False, "error": "instance_id required"}

    store = _load()
    instances = store.get("instances") if isinstance(store.get("instances"), dict) else {}
    prev = instances.get(instance_id) if isinstance(instances.get(instance_id), dict) else {}

    instances[instance_id] = {
        "instance_id": instance_id,
        "host": str(payload.get("host") or prev.get("host") or ""),
        "platform": str(payload.get("platform") or prev.get("platform") or ""),
        "source": str(payload.get("source") or prev.get("source") or "local"),
        "mode": str(payload.get("mode") or prev.get("mode") or ""),
        "profile": str(payload.get("profile") or prev.get("profile") or ""),
        "pid": payload.get("pid") or prev.get("pid"),
        "started_at": str(prev.get("started_at") or payload.get("started_at") or _iso()),
        "last_seen": _iso(),
    }

    # Keep the registry bounded: drop the oldest dead entries beyond the cap.
    if len(instances) > _MAX_INSTANCES:
        by_seen = sorted(instances.values(), key=lambda r: str(r.get("last_seen") or ""))
        for row in by_seen[: len(instances) - _MAX_INSTANCES]:
            instances.pop(str(row.get("instance_id")), None)

    ex._write_json(_INSTANCES_FILE, {"updated_at": _iso(), "instances": instances})
    return {"success": True, "instance": instances[instance_id]}


def list_instances() -> List[Dict[str, Any]]:
    store = _load()
    instances = store.get("instances") if isinstance(store.get("instances"), dict) else {}
    stale_sec = _stale_threshold_sec()
    rows: List[Dict[str, Any]] = []
    for row in instances.values():
        if not isinstance(row, dict):
            continue
        age = _age_sec(str(row.get("last_seen") or ""))
        rows.append({
            **row,
            "age_sec": round(age, 1) if age is not None else None,
            "active": age is not None and age <= stale_sec,
        })
    rows.sort(key=lambda r: (not r["active"], r["age_sec"] if r["age_sec"] is not None else float("inf")))
    return rows


def instances_summary() -> Dict[str, Any]:
    """Active instance count + double-tick conflict flag."""
    rows = list_instances()
    active = [r for r in rows if r.get("active")]
    live_active = [r for r in active if str(r.get("mode")) == "live"]
    conflict = len(active) > 1
    return {
        "instances": rows,
        "active_count": len(active),
        "live_active_count": len(live_active),
        "conflict": conflict,
        "conflict_reason": (
            "multiple daemon instances active — risk of duplicate live orders/sweeps"
            if conflict else None
        ),
    }
