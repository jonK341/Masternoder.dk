"""Revoke trophy editions on PayPal dispute/chargeback (plan 001 Q6)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clawback_trophy_edition(
    capture_id: str,
    item_id: str,
    *,
    reason: str = "paypal_dispute",
) -> Dict[str, Any]:
    from backend.services.trophy_fulfillment_service import (
        _editions_file_path,
        _read_json,
        _write_json,
        is_capture_fulfilled,
        payment_ref_for_capture,
        _CAPTURES_PATH,
    )

    cid = (capture_id or "").strip()
    iid = (item_id or "").strip()
    if not cid or not iid:
        return {"success": False, "error": "capture_id and item_id required"}
    if not is_capture_fulfilled(cid, iid):
        return {"success": False, "error": "capture_not_fulfilled"}

    ref = payment_ref_for_capture(cid, iid)
    doc = _read_json(_CAPTURES_PATH, {"captures": {}})
    capture = (doc.get("captures") or {}).get(ref) or {}
    uid = (capture.get("user_id") or "").strip()
    edition_key = (capture.get("edition_key") or "").strip()
    edition_no = capture.get("edition_no")
    if not uid or not edition_key:
        return {"success": False, "error": "edition_not_found_in_capture"}

    path = _editions_file_path(uid)
    edoc = _read_json(path, {"editions": []})
    editions = edoc.get("editions") or []
    revoked = False
    for row in editions:
        if (row.get("edition_key") or "") == edition_key:
            row["revoked"] = True
            row["revoked_at"] = _iso()
            row["revoke_reason"] = reason
            revoked = True
            break
    if not revoked:
        return {"success": False, "error": "edition_row_missing"}

    edoc["updated_at"] = _iso()
    if not _write_json(path, edoc):
        return {"success": False, "error": "write_failed"}

    try:
        from backend.services.shop_db_service import reserve_inventory

        reserve_inventory(uid, iid, 1)
    except Exception:
        pass

    try:
        from backend.services.trophy_provenance_service import append_event

        append_event(edition_key, "revoked", user_id=uid, metadata={"reason": reason, "capture_id": cid})
    except Exception:
        pass

    capture["clawed_back"] = True
    capture["clawback_reason"] = reason
    doc["captures"][ref] = capture
    _write_json(_CAPTURES_PATH, doc)

    return {"success": True, "user_id": uid, "edition_key": edition_key, "reason": reason}
