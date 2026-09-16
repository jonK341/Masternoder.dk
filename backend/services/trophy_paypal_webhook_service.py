"""PayPal webhook handler for trophy edition dispute/chargeback clawback (plan 001 Q6)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EVENTS_PATH = os.path.join(_BASE, "data", "trophy_paypal_webhook_events.jsonl")

_CLAWBACK_EVENTS = frozenset(
    {
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.REFUNDED",
        "PAYMENT.CAPTURE.REVERSED",
        "CUSTOMER.DISPUTE.CREATED",
        "CUSTOMER.DISPUTE.UPDATED",
        "CUSTOMER.DISPUTE.RESOLVED",
    }
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_already_processed(event_id: str) -> bool:
    eid = (event_id or "").strip()
    if not eid or not os.path.isfile(_EVENTS_PATH):
        return False
    try:
        with open(_EVENTS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if (row.get("event_id") or "") == eid:
                    return True
    except Exception:
        return False
    return False


def _mark_event_processed(event_id: str, payload: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_EVENTS_PATH), exist_ok=True)
        with _LOCK:
            with open(_EVENTS_PATH, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {"event_id": event_id, "at": _iso(), **payload},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    except Exception:
        pass


def _extract_capture_ids(resource: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    for key in ("id", "capture_id"):
        val = (resource.get(key) or "").strip()
        if val:
            ids.append(val)
    for link in resource.get("links") or []:
        if not isinstance(link, dict):
            continue
        href = (link.get("href") or "").strip()
        if "/captures/" in href:
            ids.append(href.rstrip("/").split("/captures/")[-1].split("?")[0])
    related = (resource.get("supplementary_data") or {}).get("related_ids") or {}
    for key in ("capture_id", "order_id"):
        val = (related.get(key) or "").strip()
        if val:
            ids.append(val)
    dispute_transactions = resource.get("disputed_transactions") or resource.get("dispute_transactions") or []
    for row in dispute_transactions:
        if not isinstance(row, dict):
            continue
        for key in ("seller_transaction_id", "buyer_transaction_id", "transaction_id"):
            val = (row.get(key) or "").strip()
            if val:
                ids.append(val)
    seen = set()
    out: List[str] = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def find_trophy_captures_by_paypal_id(capture_id: str) -> List[Dict[str, Any]]:
    """Return fulfilled trophy capture rows matching a PayPal capture / dispute id."""
    cid = (capture_id or "").strip()
    if not cid:
        return []
    from backend.services.trophy_fulfillment_service import _CAPTURES_PATH, _read_json

    doc = _read_json(_CAPTURES_PATH, {"captures": {}})
    matches: List[Dict[str, Any]] = []
    for ref, row in (doc.get("captures") or {}).items():
        if not isinstance(row, dict):
            continue
        if row.get("clawed_back"):
            continue
        edition = row.get("edition") if isinstance(row.get("edition"), dict) else {}
        paypal_cid = (row.get("paypal_capture_id") or edition.get("paypal_capture_id") or "").strip()
        if cid in ref or paypal_cid == cid or f":{cid}:" in ref or ref.endswith(f":{cid}"):
            matches.append({**row, "payment_ref": ref})
    return matches


def _cancel_auction_for_edition(user_id: str, item_id: str, edition_no: int) -> Dict[str, Any]:
    try:
        from backend.services.shop_auction_service import cancel_listing, list_user_listings

        listings = list_user_listings(user_id) or {}
        rows = listings.get("selling") or []
        cancelled = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            if (row.get("item_id") or "") != item_id:
                continue
            if int(row.get("edition_no") or 0) != int(edition_no or 0):
                continue
            lid = (row.get("listing_id") or "").strip()
            if lid:
                cancel_listing(user_id, lid)
                cancelled += 1
        return {"success": True, "cancelled": cancelled}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def process_trophy_paypal_webhook(body: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Handle PayPal dispute/refund events for trophy PayPal captures.
    Returns (json_dict, http_status). Uses 200 for handled/ignored events.
    """
    event_id = (body.get("id") or "").strip()
    event_type = (body.get("event_type") or "").strip()
    if not event_id:
        return {"success": False, "error": "missing_event_id"}, 400

    if _event_already_processed(event_id):
        return {"success": True, "duplicate": True, "event_id": event_id}, 200

    if event_type not in _CLAWBACK_EVENTS:
        _mark_event_processed(event_id, {"event_type": event_type, "ignored": True})
        return {"success": True, "ignored": True, "event_type": event_type}, 200

    resource = body.get("resource") or {}
    capture_ids = _extract_capture_ids(resource)
    if not capture_ids:
        _mark_event_processed(event_id, {"event_type": event_type, "ignored": True, "reason": "no_capture_id"})
        return {"success": True, "ignored": True, "reason": "no_capture_id", "event_type": event_type}, 200

    clawbacks: List[Dict[str, Any]] = []
    for cid in capture_ids:
        for capture in find_trophy_captures_by_paypal_id(cid):
            item_id = (capture.get("item_id") or "").strip()
            uid = (capture.get("user_id") or "").strip()
            edition_no = int(capture.get("edition_no") or 0)
            if uid and item_id and edition_no:
                _cancel_auction_for_edition(uid, item_id, edition_no)
            from backend.services.trophy_paypal_clawback_service import clawback_trophy_edition

            result = clawback_trophy_edition(cid, item_id, reason=event_type)
            clawbacks.append({"capture_id": cid, "item_id": item_id, **result})

    if not clawbacks:
        _mark_event_processed(event_id, {"event_type": event_type, "ignored": True, "reason": "no_trophy_capture"})
        return {"success": True, "ignored": True, "reason": "no_trophy_capture", "event_type": event_type}, 200

    handled = [c for c in clawbacks if c.get("success")]
    _mark_event_processed(
        event_id,
        {
            "event_type": event_type,
            "clawbacks": len(clawbacks),
            "handled": len(handled),
        },
    )
    return {
        "success": True,
        "handled": "trophy_clawback",
        "event_type": event_type,
        "clawbacks": clawbacks,
    }, 200
