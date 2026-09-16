"""Trophy PayPal fulfillment — editions, idempotency, hold, ledger proof (plan 001 U2)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CAPTURES_PATH = os.path.join(_BASE, "data", "trophy_paypal_captures.json")
_EDITION_COUNTERS_PATH = os.path.join(_BASE, "data", "trophy_edition_counters.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hold_days() -> int:
    try:
        return max(0, int(os.environ.get("TROPHY_PAYPAL_HOLD_DAYS", "14")))
    except (TypeError, ValueError):
        return 14


def is_trophy_item(item_id: str) -> bool:
    iid = (item_id or "").strip()
    if not iid:
        return False
    try:
        from backend.routes.shop_routes import _is_trophy_catalog_item

        return _is_trophy_catalog_item({"id": iid})
    except Exception:
        return iid.startswith("top25-") or iid.startswith("bundle-top25-")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with _LOCK:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        return True
    except Exception:
        return False


def payment_ref_for_capture(capture_id: str, item_id: str) -> str:
    return f"paypal:{(capture_id or '').strip()}:{(item_id or '').strip()}"


def is_capture_fulfilled(capture_id: str, item_id: str) -> bool:
    ref = payment_ref_for_capture(capture_id, item_id)
    doc = _read_json(_CAPTURES_PATH, {"captures": {}})
    return ref in (doc.get("captures") or {})


def _mark_capture_fulfilled(ref: str, payload: Dict[str, Any]) -> None:
    doc = _read_json(_CAPTURES_PATH, {"captures": {}})
    captures = doc.setdefault("captures", {})
    captures[ref] = {**payload, "fulfilled_at": _iso()}
    _write_json(_CAPTURES_PATH, doc)


def _next_edition_no(item_id: str) -> int:
    with _LOCK:
        doc = _read_json(_EDITION_COUNTERS_PATH, {"items": {}})
        items = doc.setdefault("items", {})
        n = int(items.get(item_id) or 0) + 1
        items[item_id] = n
        doc["updated_at"] = _iso()
        _write_json(_EDITION_COUNTERS_PATH, doc)
        return n


def _edition_key(item_id: str, edition_no: int) -> str:
    return f"TRO-{item_id}-{edition_no}"


def _proof_hash(user_id: str, item_id: str, edition_no: int, capture_id: str) -> str:
    raw = f"{user_id}|{item_id}|{edition_no}|{capture_id}|trophy_edition_proof"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _editions_file_path(user_id: str) -> str:
    from backend.services.shop_db_service import _safe_uid, _shop_file_root

    root = os.path.join(_shop_file_root(), "trophy_editions")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, f"{_safe_uid(user_id)}.json")


def get_trophy_editions(user_id: str, item_id: Optional[str] = None) -> List[Dict[str, Any]]:
    uid = (user_id or "").strip()
    if not uid:
        return []
    doc = _read_json(_editions_file_path(uid), {"editions": []})
    rows = [e for e in (doc.get("editions") or []) if isinstance(e, dict)]
    if item_id:
        iid = item_id.strip()
        rows = [e for e in rows if (e.get("item_id") or "") == iid]
    return rows


def _find_edition_index(editions: List[Dict[str, Any]], item_id: str, edition_no: int) -> Optional[int]:
    for idx, row in enumerate(editions):
        if not isinstance(row, dict):
            continue
        if (row.get("item_id") or "") != item_id:
            continue
        try:
            if int(row.get("edition_no") or 0) == int(edition_no):
                return idx
        except (TypeError, ValueError):
            continue
    return None


def patch_edition_fields(
    user_id: str,
    item_id: str,
    edition_no: int,
    fields: Dict[str, Any],
) -> bool:
    """Merge fields onto a stored trophy edition row."""
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    if not uid or not iid or not fields:
        return False
    path = _editions_file_path(uid)
    doc = _read_json(path, {"editions": []})
    editions = doc.get("editions") or []
    idx = _find_edition_index(editions, iid, int(edition_no))
    if idx is None:
        return False
    editions[idx] = {**editions[idx], **fields}
    doc["editions"] = editions
    doc["updated_at"] = _iso()
    return _write_json(path, doc)


def get_edition(user_id: str, item_id: str, edition_no: int) -> Optional[Dict[str, Any]]:
    rows = get_trophy_editions(user_id, item_id)
    for row in rows:
        try:
            if int(row.get("edition_no") or 0) == int(edition_no):
                return dict(row)
        except (TypeError, ValueError):
            continue
    return None


def _is_edition_held(edition: Dict[str, Any]) -> bool:
    hold = edition.get("hold_until")
    if not hold:
        return False
    try:
        hold_dt = datetime.fromisoformat(str(hold).replace("Z", "+00:00"))
        if hold_dt.tzinfo is None:
            hold_dt = hold_dt.replace(tzinfo=timezone.utc)
        return hold_dt > datetime.now(timezone.utc)
    except Exception:
        return False


def validate_edition_action(
    user_id: str,
    item_id: str,
    edition_no: int,
    action: str = "list",
) -> Dict[str, Any]:
    """Shared gate for listing, peer transfer, and other edition moves (plan 001 U6)."""
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    act = (action or "list").strip().lower()
    try:
        eno = int(edition_no)
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_edition_no"}

    edition = get_edition(uid, iid, eno)
    if not edition:
        return {"success": False, "error": "edition_not_found", "edition_no": eno}

    if _is_edition_held(edition):
        return {"success": False, "error": "edition_paypal_held", "hold_until": edition.get("hold_until")}

    if act in ("list", "transfer") and edition.get("listed_listing_id"):
        return {
            "success": False,
            "error": "edition_already_listed",
            "listed_listing_id": edition.get("listed_listing_id"),
        }

    return {"success": True, "edition": edition, "action": act}


def validate_edition_for_listing(user_id: str, item_id: str, edition_no: int) -> Dict[str, Any]:
    """Ensure a specific trophy edition can be listed on the auction house."""
    return validate_edition_action(user_id, item_id, edition_no, action="list")


def validate_edition_for_transfer(user_id: str, item_id: str, edition_no: int) -> Dict[str, Any]:
    """Ensure a specific trophy edition can be peer-transferred (plan 001 T-U2 / U6)."""
    return validate_edition_action(user_id, item_id, edition_no, action="transfer")


def transfer_edition_peer(
    *,
    sender_id: str,
    recipient_id: str,
    item_id: str,
    edition_no: int,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Gift/trade a trophy edition to another profile (plan 001 T-U2)."""
    sender = (sender_id or "").strip()
    recipient = (recipient_id or "").strip()
    iid = (item_id or "").strip()
    if not sender or sender in ("default_user", "guest"):
        return {"success": False, "error": "sender_not_authenticated"}
    if not recipient or recipient in ("default_user", "guest"):
        return {"success": False, "error": "recipient_required"}
    if sender == recipient:
        return {"success": False, "error": "cannot_transfer_to_self"}

    check = validate_edition_for_transfer(sender, iid, edition_no)
    if not check.get("success"):
        return check

    try:
        eno = int(edition_no)
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_edition_no"}

    sender_path = _editions_file_path(sender)
    sender_doc = _read_json(sender_path, {"editions": []})
    sender_editions = sender_doc.setdefault("editions", [])
    idx = _find_edition_index(sender_editions, iid, eno)
    if idx is None:
        return {"success": False, "error": "edition_not_found"}

    edition = dict(sender_editions[idx])
    transfer_event = {
        "from_user_id": sender,
        "to_user_id": recipient,
        "transferred_at": _iso(),
        "acquired_via": "peer_transfer",
        "note": (note or "").strip() or None,
    }
    history = edition.get("transfer_history")
    if not isinstance(history, list):
        history = []
    history.append(transfer_event)
    edition["transfer_history"] = history[-20:]
    edition["acquired_via"] = "peer_transfer"
    edition["transferred_from"] = sender
    edition["transferred_at"] = _iso()
    edition.pop("listed_listing_id", None)
    edition.pop("listed_at", None)

    sender_editions.pop(idx)
    sender_doc["updated_at"] = _iso()
    if not _write_json(sender_path, sender_doc):
        return {"success": False, "error": "sender_update_failed"}

    buyer_path = _editions_file_path(recipient)
    buyer_doc = _read_json(buyer_path, {"editions": []})
    buyer_editions = buyer_doc.setdefault("editions", [])
    buyer_editions.append(edition)
    buyer_doc["updated_at"] = _iso()
    if not _write_json(buyer_path, buyer_doc):
        sender_editions.insert(idx, edition)
        _write_json(sender_path, sender_doc)
        return {"success": False, "error": "recipient_update_failed"}

    try:
        from backend.services.shop_db_service import add_to_inventory, reserve_inventory

        reserve_inventory(sender, iid, 1)
        add_to_inventory(recipient, iid, edition.get("item_name") or iid, 1)
    except Exception:
        pass

    return {
        "success": True,
        "edition": edition,
        "edition_no": eno,
        "edition_key": edition.get("edition_key"),
        "sender_id": sender,
        "recipient_id": recipient,
    }


def mark_edition_listed(user_id: str, item_id: str, edition_no: int, listing_id: str) -> bool:
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    lid = (listing_id or "").strip()
    if not uid or not iid or not lid:
        return False
    path = _editions_file_path(uid)
    doc = _read_json(path, {"editions": []})
    editions = doc.setdefault("editions", [])
    idx = _find_edition_index(editions, iid, edition_no)
    if idx is None:
        return False
    editions[idx]["listed_listing_id"] = lid
    editions[idx]["listed_at"] = _iso()
    doc["updated_at"] = _iso()
    return _write_json(path, doc)


def release_edition_listing(user_id: str, item_id: str, edition_no: int) -> bool:
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    path = _editions_file_path(uid)
    doc = _read_json(path, {"editions": []})
    editions = doc.setdefault("editions", [])
    idx = _find_edition_index(editions, iid, edition_no)
    if idx is None:
        return False
    editions[idx].pop("listed_listing_id", None)
    editions[idx].pop("listed_at", None)
    editions[idx]["released_from_listing_at"] = _iso()
    doc["updated_at"] = _iso()
    return _write_json(path, doc)


def transfer_edition_to_buyer(
    *,
    seller_id: str,
    buyer_id: str,
    item_id: str,
    edition_no: int,
    listing_id: str,
    price_coins: int,
    payment_method: str = "coins",
) -> Dict[str, Any]:
    """Move a listed edition from seller to buyer with provenance."""
    seller = (seller_id or "").strip()
    buyer = (buyer_id or "").strip()
    iid = (item_id or "").strip()
    lid = (listing_id or "").strip()
    try:
        eno = int(edition_no)
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_edition_no"}

    seller_path = _editions_file_path(seller)
    seller_doc = _read_json(seller_path, {"editions": []})
    seller_editions = seller_doc.setdefault("editions", [])
    idx = _find_edition_index(seller_editions, iid, eno)
    if idx is None:
        return {"success": False, "error": "edition_not_found"}

    edition = dict(seller_editions[idx])
    if (edition.get("listed_listing_id") or "") != lid:
        return {"success": False, "error": "edition_not_reserved_for_listing"}

    transfer_event = {
        "from_user_id": seller,
        "to_user_id": buyer,
        "listing_id": lid,
        "price_coins": int(price_coins or 0),
        "payment_method": (payment_method or "coins").strip().lower(),
        "transferred_at": _iso(),
    }
    history = edition.get("transfer_history")
    if not isinstance(history, list):
        history = []
    history.append(transfer_event)
    edition["transfer_history"] = history[-20:]
    edition["acquired_via"] = "auction"
    edition["price_type"] = payment_method
    edition.pop("listed_listing_id", None)
    edition.pop("listed_at", None)
    edition["acquired_at"] = _iso()
    edition["last_listing_id"] = lid

    seller_editions.pop(idx)
    seller_doc["updated_at"] = _iso()
    if not _write_json(seller_path, seller_doc):
        return {"success": False, "error": "seller_update_failed"}

    buyer_path = _editions_file_path(buyer)
    buyer_doc = _read_json(buyer_path, {"editions": []})
    buyer_editions = buyer_doc.setdefault("editions", [])
    buyer_editions.append(edition)
    buyer_doc["updated_at"] = _iso()
    if not _write_json(buyer_path, buyer_doc):
        seller_editions.insert(idx, edition)
        _write_json(seller_path, seller_doc)
        return {"success": False, "error": "buyer_update_failed"}

    return {"success": True, "edition": edition, "edition_no": eno, "edition_key": edition.get("edition_key")}


def grant_platform_edition(
    user_id: str,
    item_id: str,
    item_name: str,
    *,
    acquired_via: str = "platform",
    price_type: str = "mn2",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Grant a new trophy edition (block mint, ops grants, etc.)."""
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    if not uid or not iid:
        return {"success": False, "error": "user_id and item_id required"}

    edition_no = _next_edition_no(iid)
    edition_key = _edition_key(iid, edition_no)
    proof_hash = _proof_hash(uid, iid, edition_no, f"{acquired_via}:{edition_no}")
    edition = {
        "item_id": iid,
        "item_name": item_name or iid,
        "edition_no": edition_no,
        "edition_key": edition_key,
        "legacy_stack": False,
        "acquired_via": acquired_via,
        "price_type": price_type,
        "proof_hash": proof_hash,
        "on_chain_mint": False,
        "granted_at": _iso(),
    }
    if extra:
        edition.update(extra)

    try:
        from backend.services.shop_db_service import fulfill_shop_purchase

        fulfill_shop_purchase(
            user_id=uid,
            item_id=iid,
            item_name=edition["item_name"],
            quantity=1,
            price_type=price_type,
            price_paid_coins=0,
            price_paid_points=None,
        )
    except Exception as exc:
        return {"success": False, "error": f"inventory_failed: {exc}"}

    _append_edition_record(uid, edition)

    try:
        from backend.services.trophy_anchor_service import queue_edition_anchor

        queue_edition_anchor(
            user_id=uid,
            item_id=iid,
            edition_no=edition_no,
            edition_key=edition_key,
            proof_hash=proof_hash,
            source=acquired_via,
        )
    except Exception:
        pass

    return {
        "success": True,
        "edition_no": edition_no,
        "edition_key": edition_key,
        "edition": edition,
        "proof_hash": proof_hash,
    }


def _append_edition_record(user_id: str, edition: Dict[str, Any]) -> None:
    path = _editions_file_path(user_id)
    doc = _read_json(path, {"editions": []})
    editions = doc.setdefault("editions", [])
    editions.append(edition)
    doc["updated_at"] = _iso()
    _write_json(path, doc)


def fulfill_trophy_paypal(
    *,
    user_id: str,
    item_id: str,
    item_name: str,
    order_id: str,
    capture_id: str,
    amount_usd: float,
) -> Dict[str, Any]:
    """Idempotent trophy grant after PayPal capture."""
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    cid = (capture_id or order_id or "").strip()
    if not uid or not iid or not cid:
        return {"success": False, "error": "user_id, item_id, and capture_id required"}

    ref = payment_ref_for_capture(cid, iid)
    if is_capture_fulfilled(cid, iid):
        prior = (_read_json(_CAPTURES_PATH, {}).get("captures") or {}).get(ref) or {}
        return {
            "success": True,
            "duplicate": True,
            "payment_ref": ref,
            "edition": prior.get("edition"),
            "edition_no": prior.get("edition_no"),
            "edition_key": prior.get("edition_key"),
        }

    from backend.services.trophy_pricing_service import get_effective_price

    pricing = get_effective_price(iid)
    if not pricing.get("success"):
        return {"success": False, "error": pricing.get("error", "pricing_failed")}

    expected = float(pricing.get("effective_price_usd") or 0)
    if amount_usd > 0 and expected > 0 and abs(float(amount_usd) - expected) > 0.02:
        return {
            "success": False,
            "error": "amount_mismatch",
            "expected_usd": expected,
            "captured_usd": float(amount_usd),
        }

    edition_no = _next_edition_no(iid)
    edition_key = _edition_key(iid, edition_no)
    hold_until = (datetime.now(timezone.utc) + timedelta(days=_hold_days())).isoformat().replace("+00:00", "Z")
    proof_hash = _proof_hash(uid, iid, edition_no, cid)
    granted_at = _iso()

    edition = {
        "item_id": iid,
        "item_name": item_name or pricing.get("name") or iid,
        "edition_no": edition_no,
        "edition_key": edition_key,
        "legacy_stack": False,
        "acquired_via": "paypal",
        "price_type": "paypal",
        "payment_ref": ref,
        "paypal_order_id": order_id,
        "paypal_capture_id": cid,
        "amount_usd": float(amount_usd or expected),
        "hold_until": hold_until,
        "proof_hash": proof_hash,
        "on_chain_mint": False,
        "granted_at": granted_at,
    }

    try:
        from backend.services.shop_db_service import fulfill_shop_purchase

        fulfill_shop_purchase(
            user_id=uid,
            item_id=iid,
            item_name=edition["item_name"],
            quantity=1,
            price_type="paypal",
            price_paid_coins=0,
            price_paid_points=None,
        )
    except Exception as exc:
        return {"success": False, "error": f"inventory_failed: {exc}"}

    _append_edition_record(uid, edition)

    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            uid,
            "trophy_edition_proof",
            float(amount_usd or expected),
            txid=ref,
            metadata={
                "item_id": iid,
                "edition_no": edition_no,
                "edition_key": edition_key,
                "proof_hash": proof_hash,
                "hold_until": hold_until,
                "paypal_capture_id": cid,
                "on_chain_mint": False,
            },
        )
    except Exception:
        pass

    try:
        from backend.routes.shop_routes import _apply_shop_item_effects, _get_shop_items

        full_item = next((i for i in (_get_shop_items() or []) if (i.get("id") or "") == iid), {"id": iid, "name": edition["item_name"]})
        _apply_shop_item_effects(uid, iid, full_item, 1, purchase_ref=cid)
    except Exception:
        pass

    _mark_capture_fulfilled(
        ref,
        {
            "user_id": uid,
            "item_id": iid,
            "edition_no": edition_no,
            "edition_key": edition_key,
            "edition": edition,
        },
    )

    try:
        from backend.services.trophy_anchor_service import queue_edition_anchor

        queue_edition_anchor(
            user_id=uid,
            item_id=iid,
            edition_no=edition_no,
            edition_key=edition_key,
            proof_hash=proof_hash,
            source="paypal",
        )
    except Exception:
        pass

    return {
        "success": True,
        "duplicate": False,
        "payment_ref": ref,
        "item_granted": iid,
        "edition_no": edition_no,
        "edition_key": edition_key,
        "hold_until": hold_until,
        "proof_hash": proof_hash,
        "edition": edition,
        "on_chain_mint": False,
    }
