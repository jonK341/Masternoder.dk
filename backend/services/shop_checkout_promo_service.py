"""
Shop-wide promo codes — redeem bonuses + PayPal checkout discounts (#10).

Sources: data/discord_promo_codes.json (M8) + monetization_config.shop_promo_codes.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DISCORD_PATH = os.path.join(_BASE, "data", "discord_promo_codes.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_discord() -> Dict[str, Any]:
    if not os.path.isfile(_DISCORD_PATH):
        return {"codes": []}
    try:
        with open(_DISCORD_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"codes": []}
    except Exception:
        return {"codes": []}


def _config_promos() -> list:
    try:
        from backend.services.monetization_config_service import _load_raw

        raw = _load_raw()
        rows = raw.get("shop_promo_codes")
        return list(rows) if isinstance(rows, list) else []
    except Exception:
        return []


def _find_code(code: str) -> Optional[Dict[str, Any]]:
    c = (code or "").strip().upper()
    if not c:
        return None
    for row in _config_promos():
        if isinstance(row, dict) and str(row.get("code") or "").upper() == c:
            return {**row, "_source": "config"}
    data = _load_discord()
    for row in data.get("codes") or []:
        if isinstance(row, dict) and str(row.get("code") or "").upper() == c:
            return {**row, "_source": "discord"}
    return None


def _expired(row: Dict[str, Any]) -> bool:
    exp = row.get("expires_at")
    if not exp:
        return False
    try:
        dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > dt
    except Exception:
        return False


def validate_checkout_promo(
    code: str,
    user_id: str,
    *,
    amount_usd: float,
) -> Dict[str, Any]:
    """Validate promo for PayPal checkout; returns discount + bonus metadata."""
    uid = (user_id or "").strip()
    row = _find_code(code)
    if not row:
        return {"success": False, "error": "invalid_code"}
    if _expired(row):
        return {"success": False, "error": "expired"}

    redeemed = row.get("redeemed_by") if isinstance(row.get("redeemed_by"), list) else []
    max_r = int(row.get("max_redemptions") or 999999)
    if len(redeemed) >= max_r:
        return {"success": False, "error": "exhausted"}

    per_user_once = row.get("per_user_once", True)
    if per_user_once and uid and uid in redeemed:
        return {"success": False, "error": "already_redeemed"}

    try:
        disc = float(row.get("discount_percent") or row.get("paypal_discount_percent") or 0)
    except (TypeError, ValueError):
        disc = 0.0
    disc = max(0.0, min(disc, 90.0))
    discounted = round(float(amount_usd) * (1.0 - disc / 100.0), 2) if disc > 0 else float(amount_usd)
    if discounted < 0.5:
        discounted = 0.5

    bonus_coins = int(row.get("bonus_coins_on_purchase") or row.get("reward_coins") or 0)
    affiliate = (row.get("affiliate_id") or row.get("campaign_id") or "").strip() or None

    return {
        "success": True,
        "code": str(row.get("code") or "").upper(),
        "discount_percent": disc,
        "amount_usd_original": round(float(amount_usd), 2),
        "amount_usd_discounted": discounted,
        "bonus_coins_on_capture": bonus_coins,
        "affiliate_id": affiliate,
        "source": row.get("_source"),
    }


def apply_discounted_amount(amount_usd: float, promo_code: Optional[str], user_id: str) -> Tuple[float, Dict[str, Any]]:
    if not promo_code:
        return float(amount_usd), {"promo_applied": False}
    v = validate_checkout_promo(promo_code, user_id, amount_usd=float(amount_usd))
    if not v.get("success"):
        return float(amount_usd), {"promo_applied": False, "promo_error": v.get("error")}
    return float(v["amount_usd_discounted"]), {"promo_applied": True, **v}


def record_promo_redemption(code: str, user_id: str) -> None:
    """Mark promo used after successful capture (best-effort)."""
    c = (code or "").strip().upper()
    if not c or not user_id:
        return
    # Discord file
    data = _load_discord()
    changed = False
    for row in data.get("codes") or []:
        if str(row.get("code") or "").upper() == c:
            rb = row.get("redeemed_by") if isinstance(row.get("redeemed_by"), list) else []
            if user_id not in rb:
                rb.append(user_id)
                row["redeemed_by"] = rb
                changed = True
            break
    if changed:
        try:
            with _LOCK:
                tmp = _DISCORD_PATH + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(tmp, _DISCORD_PATH)
        except Exception:
            pass
