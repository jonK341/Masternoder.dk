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


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)


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
