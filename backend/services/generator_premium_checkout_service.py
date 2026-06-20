"""
Premium per-render PayPal quote (#6) — HD / long / studio bumps before pipeline.
"""
from __future__ import annotations

from typing import Any, Dict


def _tier_multiplier(config: Dict[str, Any]) -> float:
    qm = str(config.get("quality_mode") or "auto").lower()
    ep = str(config.get("encode_profile") or "").lower()
    dur = int(config.get("duration") or 90)
    mult = 1.0
    if qm in ("hd", "high", "pro") or ep in ("hd", "high"):
        mult = max(mult, 1.5)
    if qm in ("studio", "ultra"):
        mult = max(mult, 2.0)
    if dur > 180:
        mult = max(mult, 1.25)
    if dur > 300:
        mult = max(mult, 1.5)
    return mult


def quote_premium_render(user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """USD price for premium options beyond standard tier allowance."""
    try:
        from backend.services.cogs_metering_service import estimate_reference_job_usd
        from backend.services.monetization_config_service import get_credit_reference_fraction
    except Exception as e:
        return {"success": False, "error": str(e)}

    ref = float((estimate_reference_job_usd() or {}).get("total_usd") or 0.15)
    mult = _tier_multiplier(config or {})
    target_margin = 0.35
    base_usd = ref * mult / max(0.01, (1.0 - target_margin))
    price_usd = max(0.99, round(base_usd, 2))
    frac = get_credit_reference_fraction()
    credits = round(mult / max(frac, 0.01), 2) if frac else mult

    return {
        "success": True,
        "user_id": user_id,
        "price_usd": price_usd,
        "generation_credits_equivalent": credits,
        "quality_multiplier": mult,
        "premium_required": mult > 1.01,
        "checkout": {
            "create_order": "POST /api/monetization/premium-render/create-order",
            "item_id_prefix": "premium-render-",
        },
    }


def create_premium_order(user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    import os
    import urllib.parse

    q = quote_premium_render(user_id, config)
    if not q.get("success"):
        return q
    if not q.get("premium_required"):
        return {"success": True, "premium_required": False, "price_usd": 0}
    uid = (user_id or "").strip()
    price = float(q["price_usd"])
    item_id = "premium-render-unlock"
    base = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    return_url = f"{base}/generator?paypal_premium=success&user_id={urllib.parse.quote(uid)}"
    cancel_url = f"{base}/generator?paypal_premium=cancel"
    try:
        from backend.services.paypal_service import create_order

        result = create_order(
            amount=price,
            currency="USD",
            item_name="Premium video generation unlock",
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": item_id, "user_id": uid, "product": "premium_render"},
        )
    except Exception as e:
        return {"success": False, "error": str(e)}
    if not result.get("success"):
        return result
    return {
        "success": True,
        "premium_required": True,
        "order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "price_usd": price,
        "quote": q,
    }
