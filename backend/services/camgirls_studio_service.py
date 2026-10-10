"""Camgirls studio catalog — gifts, dances, tip menu."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CATALOG_FILE = os.path.join(_ROOT, "data", "camgirls_studio_catalog.json")


def studio_catalog() -> Dict[str, Any]:
    if not os.path.isfile(_CATALOG_FILE):
        return {"success": False, "error": "catalog_missing"}
    try:
        with open(_CATALOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"success": False, "error": "invalid_catalog"}
        return {"success": True, **data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tip_with_gift(
    user_id: str,
    performer_id: str,
    *,
    gift_id: Optional[str] = None,
    amount_mn2: Optional[float] = None,
) -> Dict[str, Any]:
    from backend.services.camgirls_service import _is_age_verified, _is_unlocked, tip_performer

    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    if not _is_unlocked(user_id, performer_id):
        return {"success": False, "code": "unlock_required"}
    cat = studio_catalog()
    if not cat.get("success"):
        return cat
    gifts = cat.get("gifts") or {}
    label = None
    if gift_id:
        gift = gifts.get(gift_id)
        if not gift:
            return {"success": False, "error": "gift_not_found"}
        price = float(gift.get("price_mn2") or 5)
        label = gift.get("label") or gift_id
    else:
        price = float(amount_mn2 or 0)
        if price <= 0:
            return {"success": False, "error": "gift_id_or_amount_required"}
    result = tip_performer(user_id, performer_id, price, gift_id=gift_id)
    if not result.get("success"):
        return result
    out = dict(result)
    if gift_id:
        out["gift_id"] = gift_id
        out["gift_label"] = label
    return out


def request_dance(user_id: str, performer_id: str, dance_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import _is_age_verified, _is_unlocked, tip_performer

    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    if not _is_unlocked(user_id, performer_id):
        return {"success": False, "code": "unlock_required"}
    cat = studio_catalog()
    if not cat.get("success"):
        return cat
    dances = cat.get("dances") or {}
    dance = dances.get(dance_id)
    if not dance:
        return {"success": False, "error": "dance_not_found"}
    price = float(dance.get("price_mn2") or 8)
    result = tip_performer(user_id, performer_id, price, dance_id=dance_id)
    if not result.get("success"):
        return result
    return {
        **result,
        "dance_id": dance_id,
        "dance_label": dance.get("label") or dance_id,
    }
