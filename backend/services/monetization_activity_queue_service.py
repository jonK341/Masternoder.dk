"""Activity queue — paid masternode renters and monetization stream events for ops + SSE."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_QUEUE_PATH = os.path.join(_BASE, "logs", "monetization_activity_queue.jsonl")
_SEEN_PATH = os.path.join(_BASE, "logs", "monetization_activity_queue_seen.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_seen() -> Set[str]:
    if not os.path.isfile(_SEEN_PATH):
        return set()
    try:
        with open(_SEEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        keys = data.get("keys") if isinstance(data, dict) else data
        if isinstance(keys, list):
            return {str(k) for k in keys}
    except Exception:
        pass
    return set()


def _save_seen(keys: Set[str]) -> None:
    os.makedirs(os.path.dirname(_SEEN_PATH), exist_ok=True)
    with _LOCK:
        with open(_SEEN_PATH, "w", encoding="utf-8") as f:
            json.dump({"updated_at": _iso(), "keys": sorted(keys)[-5000:]}, f, indent=2)


def _append_queue(row: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(os.path.dirname(_QUEUE_PATH), exist_ok=True)
    with _LOCK:
        with open(_QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
    try:
        from backend.services.activity_events_service import emit

        emit(
            row.get("type") or "monetization_queue",
            user_id=row.get("user_id"),
            channel=row.get("channel") or "monetization",
            text=row.get("text"),
            payload=row.get("payload") if isinstance(row.get("payload"), dict) else row,
        )
    except Exception:
        pass
    return row


def list_paid_renters() -> List[Dict[str, Any]]:
    """Paying users with active or provisioning masternode rental (orders + fleet registry)."""
    rows: List[Dict[str, Any]] = []
    seen_users: Set[str] = set()

    try:
        from backend.services import mn2_masternode_hosting_service as hosting

        orders = hosting._load_orders()
        for oid, order in orders.items():
            if not isinstance(order, dict) or order.get("status") != "paid":
                continue
            uid = str(order.get("user_id") or "").strip()
            if not uid:
                continue
            host_ids = [str(h) for h in (order.get("host_ids") or []) if h]
            rows.append({
                "source": "hosting_order",
                "order_id": order.get("order_id") or oid,
                "user_id": uid,
                "host_ids": host_ids,
                "slots": int(order.get("slots") or len(host_ids) or 1),
                "usd_total": float(order.get("usd_total") or 0),
                "payment_method": order.get("payment_method"),
                "paid_at": order.get("paid_at"),
            })
            seen_users.add(uid)
    except Exception:
        pass

    try:
        from backend.services import mn2_masternode_service as mn

        active_status = {"enabled", "provisioning", "planned", "queued", "active"}
        for host in mn.list_hosts(include_internal=False):
            if not isinstance(host, dict):
                continue
            uid = str(host.get("owner_user_id") or "").strip()
            if not uid:
                continue
            st = str(host.get("status") or "").lower()
            if st and st not in active_status:
                continue
            hid = str(host.get("id") or "")
            if not hid:
                continue
            if any(r.get("user_id") == uid and hid in (r.get("host_ids") or []) for r in rows):
                continue
            rows.append({
                "source": "fleet_registry",
                "order_id": None,
                "user_id": uid,
                "host_ids": [hid],
                "slots": 1,
                "usd_total": None,
                "payment_method": "hosting",
                "paid_at": host.get("created_at") or host.get("updated_at"),
                "host_status": host.get("status"),
            })
    except Exception:
        pass

    rows.sort(key=lambda r: str(r.get("paid_at") or ""), reverse=True)
    return rows


def enqueue_renter(row: Dict[str, Any], *, force: bool = False) -> Dict[str, Any]:
    """Idempotent enqueue for one paid renter row."""
    uid = str(row.get("user_id") or "").strip()
    order_id = str(row.get("order_id") or "").strip()
    host_ids = row.get("host_ids") or []
    dedupe_key = f"hosting_order:{order_id}" if order_id else f"host:{host_ids[0]}" if host_ids else f"user:{uid}"
    if not uid:
        return {"enqueued": False, "reason": "missing_user_id"}

    seen = _load_seen()
    if dedupe_key in seen and not force:
        return {"enqueued": False, "reason": "already_queued", "dedupe_key": dedupe_key}

    slots = int(row.get("slots") or len(host_ids) or 1)
    usd = row.get("usd_total")
    pay = row.get("payment_method") or "paypal"
    text = f"Paid masternode renter — {slots} slot(s) for {uid}"
    if usd is not None:
        text += f" (${float(usd):.2f} via {pay})"

    item = {
        "ts": _iso(),
        "type": "masternode_rental",
        "channel": "hosting",
        "user_id": uid,
        "text": text,
        "dedupe_key": dedupe_key,
        "priority": "high" if float(usd or 0) > 0 else "normal",
        "payload": {
            "order_id": order_id or None,
            "host_ids": host_ids,
            "slots": slots,
            "usd_total": usd,
            "payment_method": pay,
            "source": row.get("source"),
            "stream_id": "masternode-hosting",
            "revenue_track_ids": ["A3", "E6"],
        },
    }
    _append_queue(item)
    seen.add(dedupe_key)
    _save_seen(seen)
    return {"enqueued": True, "item": item}


def sync_rented_masternodes_to_queue(*, force: bool = False) -> Dict[str, Any]:
    """Scan paid hosting orders + fleet registry; enqueue new renters to activity queue."""
    renters = list_paid_renters()
    enqueued = 0
    skipped = 0
    items: List[Dict[str, Any]] = []
    for row in renters:
        result = enqueue_renter(row, force=force)
        if result.get("enqueued"):
            enqueued += 1
            items.append(result.get("item") or {})
        else:
            skipped += 1
    return {
        "success": True,
        "scanned": len(renters),
        "enqueued": enqueued,
        "skipped": skipped,
        "items": items[:20],
        "synced_at": _iso(),
    }


def list_queue(limit: int = 50, *, channel: Optional[str] = None) -> List[Dict[str, Any]]:
    safe = max(1, min(int(limit or 50), 200))
    if not os.path.isfile(_QUEUE_PATH):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(_QUEUE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if channel and row.get("channel") != channel:
                        continue
                    rows.append(row)
                except Exception:
                    continue
    except Exception:
        return []
    return list(reversed(rows[-safe:]))


def queue_stats() -> Dict[str, Any]:
    renters = list_paid_renters()
    recent = list_queue(limit=100)
    by_type: Dict[str, int] = {}
    for row in recent:
        t = str(row.get("type") or "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "paid_renters": len(renters),
        "queue_depth_recent": len(recent),
        "by_type": by_type,
        "seen_keys": len(_load_seen()),
    }
