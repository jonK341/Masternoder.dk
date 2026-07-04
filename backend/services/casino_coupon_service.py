"""Lab / cross-promo casino coupons (Wave 3)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services import casino_service as cs


def _codes() -> Dict[str, Dict[str, Any]]:
    cfg = cs._load_config()
    block = cfg.get("lab_coupons") if isinstance(cfg.get("lab_coupons"), dict) else {}
    raw = block.get("codes") if isinstance(block.get("codes"), dict) else {}
    return {str(k).upper(): v for k, v in raw.items() if isinstance(v, dict)}


def redeem(user_id: str, code: str) -> Dict[str, Any]:
    cfg = cs._load_config()
    block = cfg.get("lab_coupons") if isinstance(cfg.get("lab_coupons"), dict) else {}
    if not block.get("enabled", True):
        return {"success": False, "error": "coupons_disabled"}
    user_id = (user_id or "").strip()
    key = (code or "").strip().upper()
    tmpl = _codes().get(key)
    if not tmpl:
        return {"success": False, "error": "unknown_coupon"}
    import json
    import os

    log_dir = cs._log_dir()
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, "casino_coupon_redemptions.json")
    redemptions: Dict[str, Any] = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            redemptions = data if isinstance(data, dict) else {}
        except Exception:
            redemptions = {}
    user_key = f"{user_id}:{key}"
    if user_key in (redemptions or {}):
        return {"success": False, "error": "already_redeemed"}
    ctype = str(tmpl.get("type") or "")
    result: Dict[str, Any] = {"coupon": key, "type": ctype, "label": tmpl.get("label")}
    if ctype == "free_daily_bet":
        r = cs.play_free_daily_bet(user_id, "heads")
        if not r.get("success"):
            return r
        result["free_bet"] = r
    elif ctype == "crew_invite_boost":
        result["crew_invite_boost"] = True
        result["message"] = "Crew lobby priority enabled for your next crash crew room."
    else:
        return {"success": False, "error": "unsupported_coupon_type"}
    redemptions[user_key] = {"user_id": user_id, "code": key, "type": ctype}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(redemptions, f, ensure_ascii=False, indent=2)
    except OSError:
        return {"success": False, "error": "coupon_store_failed"}
    return {"success": True, **result}
