"""
Reliable webhook outbox — enqueue, process, retry, dead-letter.

Storage: data/webhook_outbox.jsonl (append-only)
Dead letters: logs/webhook_dead_letter.jsonl
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_OUTBOX = os.path.join(_BASE, "data", "webhook_outbox.jsonl")
_DEAD = os.path.join(_BASE, "logs", "webhook_dead_letter.jsonl")
_MAX_ATTEMPTS = 5


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _append(path: str, row: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_all() -> List[Dict[str, Any]]:
    if not os.path.isfile(_OUTBOX):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(_OUTBOX, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return rows


def _rewrite(rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(_OUTBOX), exist_ok=True)
    tmp = _OUTBOX + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, _OUTBOX)


def enqueue(
    source: str,
    event_key: str,
    payload: Dict[str, Any],
    *,
    handler: str,
) -> Dict[str, Any]:
    """Idempotent on (source, event_key) if already enqueued or done."""
    src = (source or "").strip()
    key = (event_key or "").strip()
    for r in _read_all():
        if r.get("source") == src and r.get("event_key") == key:
            status = r.get("status")
            if status in ("done", "pending", "processing"):
                return {"success": True, "duplicate": True, "id": r.get("id"), "status": status}
    row = {
        "id": "wh_" + uuid.uuid4().hex[:16],
        "source": src,
        "event_key": key,
        "handler": handler,
        "payload": payload,
        "status": "pending",
        "attempts": 0,
        "created_at": _iso(),
        "updated_at": _iso(),
        "last_error": None,
        "next_retry_at": _iso(),
    }
    _append(_OUTBOX, row)
    return {"success": True, "id": row["id"], "duplicate": False}


def _dispatch(handler: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    h = (handler or "").strip()
    if h == "p2p_paypal":
        from backend.services import mn2_p2p_service as p2p
        sig = bool(payload.get("signature_ok"))
        return p2p.handle_webhook(payload.get("event") or {}, sig)
    if h == "paypal_subscription":
        from backend.services.monetization_subscription_service import process_paypal_webhook_event
        return process_paypal_webhook_event(payload.get("event") or {})
    return {"success": False, "error": f"unknown handler {h}"}


def process_one(row: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(row)
    row["attempts"] = int(row.get("attempts") or 0) + 1
    row["updated_at"] = _iso()
    try:
        result = _dispatch(row.get("handler") or "", row.get("payload") or {})
        ok = bool(result.get("success", True)) and not result.get("error")
        if ok or result.get("duplicate"):
            row["status"] = "done"
            row["result"] = result
        else:
            row["status"] = "failed"
            row["last_error"] = str(result.get("error") or result)
    except Exception as e:
        row["status"] = "failed"
        row["last_error"] = str(e)
    return row


def process_pending(limit: int = 50) -> Dict[str, Any]:
    rows = _read_all()
    updated = []
    processed = 0
    failed = 0
    dead = 0
    for i, r in enumerate(rows):
        if r.get("status") not in ("pending", "failed"):
            updated.append(r)
            continue
        if processed >= limit:
            updated.append(r)
            continue
        if int(r.get("attempts") or 0) >= _MAX_ATTEMPTS:
            r["status"] = "dead_letter"
            _append(_DEAD, r)
            dead += 1
            updated.append(r)
            continue
        nr = process_one(r)
        processed += 1
        if nr.get("status") == "done":
            pass
        else:
            failed += 1
        updated.append(nr)
    _rewrite(updated)
    return {"success": True, "processed": processed, "failed": failed, "dead_letter": dead}


def stats() -> Dict[str, Any]:
    rows = _read_all()
    counts: Dict[str, int] = {}
    for r in rows:
        st = r.get("status") or "unknown"
        counts[st] = counts.get(st, 0) + 1
    return {"success": True, "total": len(rows), "by_status": counts}


def process_inline(source: str, event_key: str, payload: Dict[str, Any], handler: str) -> Dict[str, Any]:
    """Enqueue then process immediately (used from HTTP handlers)."""
    enq = enqueue(source, event_key, payload, handler=handler)
    if enq.get("duplicate"):
        return {"success": True, "duplicate": True, "id": enq.get("id"), "status": enq.get("status")}
    rows = _read_all()
    target = next((r for r in rows if r.get("id") == enq.get("id")), None)
    if not target:
        return {"success": False, "error": "enqueue failed"}
    done = process_one(target)
    all_rows = _read_all()
    for i, r in enumerate(all_rows):
        if r.get("id") == done.get("id"):
            all_rows[i] = done
            break
    _rewrite(all_rows)
    return done.get("result") or done
