"""Burn trophy edition for MN2 shop credit (polish)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def burn_edition(user_id: str, item_id: str, edition_no: int) -> Dict[str, Any]:
    from backend.services.trophy_fulfillment_service import (
        _editions_file_path,
        _find_edition_index,
        _read_json,
        _write_json,
        validate_edition_for_transfer,
    )

    uid = (user_id or "").strip()
    check = validate_edition_for_transfer(uid, item_id, edition_no)
    if not check.get("success"):
        return check

    path = _editions_file_path(uid)
    doc = _read_json(path, {"editions": []})
    editions = doc.get("editions") or []
    idx = _find_edition_index(editions, item_id, int(edition_no))
    if idx is None:
        return {"success": False, "error": "edition_not_found"}

    edition = editions.pop(idx)
    ekey = edition.get("edition_key") or ""
    doc["updated_at"] = _iso()
    if not _write_json(path, doc):
        return {"success": False, "error": "write_failed"}

    credit_mn2 = 0.05
    try:
        from backend.services.unified_points_database import unified_points_db

        unified_points_db.add_points(
            user_id=uid,
            point_type="mn2_balance",
            amount=credit_mn2,
            source="trophy_burn",
            metadata={"edition_key": ekey, "item_id": item_id},
        )
    except Exception:
        pass

    try:
        from backend.services.trophy_provenance_service import append_event

        append_event(ekey, "burned", user_id=uid, metadata={"credit_mn2": credit_mn2})
    except Exception:
        pass

    try:
        from backend.services.shop_db_service import reserve_inventory

        reserve_inventory(uid, item_id, 1)
    except Exception:
        pass

    return {"success": True, "edition_key": ekey, "credit_mn2": credit_mn2, "burned": True}
