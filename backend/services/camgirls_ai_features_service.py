"""
Camgirl AI feature bundles — animation + payment + sound for wallet v2.
Catalog: data/camgirls_ai_features_catalog.json
"""
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_LOCK = threading.RLock()
_GUEST_IDS = frozenset({"", "default_user", "guest"})


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _catalog_path() -> str:
    return os.path.join(_base(), "data", "camgirls_ai_features_catalog.json")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_catalog() -> Dict[str, Any]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    path = _catalog_path()
    if not os.path.isfile(path):
        _CATALOG_CACHE = {"version": 1, "total": 0, "categories": [], "features": []}
        return _CATALOG_CACHE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {"version": 1, "total": 0, "categories": [], "features": []}
    except Exception:
        data = {"version": 1, "total": 0, "categories": [], "features": []}
    _CATALOG_CACHE = data
    return data


def _feature_index() -> Dict[str, Dict[str, Any]]:
    doc = load_catalog()
    out: Dict[str, Dict[str, Any]] = {}
    for feat in doc.get("features") or []:
        if isinstance(feat, dict) and feat.get("id"):
            out[str(feat["id"])] = feat
    return out


def get_feature_by_id(feature_id: str) -> Optional[Dict[str, Any]]:
    return _feature_index().get((feature_id or "").strip())


def _performer_allowed(feature: Dict[str, Any], performer_id: Optional[str]) -> bool:
    ids = feature.get("performer_ids") or []
    if not ids or "all" in ids:
        return True
    pid = (performer_id or "").strip()
    if not pid:
        return False
    return pid in ids


def _default_performer(feature: Dict[str, Any]) -> Optional[str]:
    ids = feature.get("performer_ids") or []
    if "all" in ids or not ids:
        return None
    return str(ids[0])


def _user_has_upgrade_unlock(user_id: str, upgrade_id: Optional[str]) -> bool:
    if not upgrade_id:
        return False
    from backend.services.camgirls_wallet_service import load_user_progress
    progress = load_user_progress(user_id)
    return str(upgrade_id) in (progress.get("unlocked_ids") or [])


def _enrich_feature(
    feature: Dict[str, Any],
    user_id: Optional[str] = None,
    performer_id: Optional[str] = None,
) -> Dict[str, Any]:
    row = dict(feature)
    payment = dict(row.get("payment") or {})
    unlock_id = payment.get("unlock_upgrade_id")
    unlocked = False
    if user_id and unlock_id:
        unlocked = _user_has_upgrade_unlock(user_id, str(unlock_id))
    effective_price = 0.0 if unlocked else float(payment.get("price_mn2") or 0)
    payment["effective_price_mn2"] = round(effective_price, 8)
    payment["unlocked_via_upgrade"] = unlocked
    row["payment"] = payment
    row["performer_match"] = _performer_allowed(feature, performer_id)
    return row


def list_features(
    category: Optional[str] = None,
    performer_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    doc = load_catalog()
    features = doc.get("features") or []
    if category:
        cat = category.strip().lower()
        features = [f for f in features if isinstance(f, dict) and (f.get("category") or "").lower() == cat]
    if performer_id:
        features = [f for f in features if isinstance(f, dict) and _performer_allowed(f, performer_id)]
    enriched = [_enrich_feature(f, user_id=user_id, performer_id=performer_id) for f in features]
    return {
        "success": True,
        "version": doc.get("version", 1),
        "total": len(enriched),
        "categories": doc.get("categories") or [],
        "features": enriched,
    }


def get_feature_detail(
    feature_id: str,
    performer_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    feature = get_feature_by_id(feature_id)
    if not feature:
        return {"success": False, "error": "feature_not_found", "feature_id": feature_id}
    return {
        "success": True,
        "feature": _enrich_feature(feature, user_id=user_id, performer_id=performer_id),
    }


def trigger_feature(
    user_id: str,
    feature_id: str,
    performer_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Pay MN2 (or free if upgrade-unlocked) and return animation+sound playback payload."""
    user_id = (user_id or "").strip() or "default_user"
    feature_id = (feature_id or "").strip()
    if user_id in _GUEST_IDS:
        return {"success": False, "error": "guest_cannot_trigger", "message": "Sign in to trigger AI features."}

    feature = get_feature_by_id(feature_id)
    if not feature:
        return {"success": False, "error": "feature_not_found", "feature_id": feature_id}

    pid = (performer_id or _default_performer(feature) or "").strip()
    if not _performer_allowed(feature, pid):
        return {
            "success": False,
            "error": "performer_not_allowed",
            "message": "This feature is not available for the selected performer.",
            "performer_id": pid or None,
        }

    payment = feature.get("payment") if isinstance(feature.get("payment"), dict) else {}
    unlock_id = payment.get("unlock_upgrade_id")
    unlocked = _user_has_upgrade_unlock(user_id, str(unlock_id) if unlock_id else None)
    price = 0.0 if unlocked else float(payment.get("price_mn2") or 0)
    tip_min = float(payment.get("tip_min_mn2") or 0)

    transfer_result = None
    credited_performer = None
    if price > 0:
        if price < tip_min:
            return {"success": False, "error": "below_minimum", "tip_min_mn2": tip_min}
        if not pid:
            return {
                "success": False,
                "error": "performer_required",
                "message": "Select a performer to credit MN2 for this feature.",
            }
        from backend.services.camgirls_wallet_service import ensure_wallet, wallet_user_id_for
        wallet_detail = ensure_wallet(pid)
        if not wallet_detail.get("success"):
            return wallet_detail
        recipient = wallet_detail["wallet_user_id"]
        from backend.services.mn2_gift_service import transfer
        note = f"camgirl_ai_feature:{feature_id}:{pid}"
        transfer_result = transfer(user_id, recipient, price, note=note)
        if not transfer_result.get("success"):
            return {
                "success": False,
                "error": transfer_result.get("error") or "transfer_failed",
                "message": transfer_result.get("message"),
                "transfer": transfer_result,
            }
        credited_performer = {
            "camgirl_id": pid,
            "wallet_user_id": recipient,
            "amount_mn2": price,
        }

    animation = feature.get("animation") if isinstance(feature.get("animation"), dict) else {}
    sound = feature.get("sound") if isinstance(feature.get("sound"), dict) else {}

    return {
        "success": True,
        "feature_id": feature_id,
        "name": feature.get("name"),
        "category": feature.get("category"),
        "performer_id": pid or None,
        "paid_mn2": round(price, 8),
        "unlocked_via_upgrade": unlocked,
        "unlock_upgrade_id": unlock_id,
        "transfer": transfer_result,
        "performer_credit": credited_performer,
        "playback": {
            "animation": animation,
            "sound": sound,
            "triggered_at": _iso_now(),
        },
    }
