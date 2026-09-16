"""
Studio Cash Rail — self-serve PayPal deposit for B2B SKUs (#2).
"""
from __future__ import annotations

import urllib.parse
from typing import Any, Dict, Optional


def list_scr_checkout_skus() -> Dict[str, Any]:
    from backend.services.monetization_config_service import get_b2b_studio_skus

    skus = []
    for s in get_b2b_studio_skus():
        price = float(s.get("list_price_usd") or 0)
        if price <= 0:
            continue
        skus.append({
            "id": s.get("id"),
            "label": s.get("label"),
            "description": s.get("description"),
            "list_price_usd": price,
            "currency": s.get("currency") or "USD",
            "generation_credits_pool": s.get("generation_credits_pool"),
            "term_days": s.get("term_days"),
        })
    return {"success": True, "skus": skus}


def create_scr_deposit_order(
    user_id: str,
    studio_sku_id: str,
    *,
    org_label: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services.monetization_config_service import get_b2b_studio_sku

    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "account_required"}
    sku = get_b2b_studio_sku(studio_sku_id)
    if not sku:
        return {"success": False, "error": "unknown_studio_sku"}
    price = float(sku.get("list_price_usd") or 0)
    if price <= 0:
        return {"success": False, "error": "sku_not_self_serve", "hint": "Contact sales for custom pricing."}
    item_id = f"scr-{studio_sku_id}"
    base = ( __import__("os").environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    return_url = (
        f"{base}/shop?paypal=success&scr_deposit=1&studio_sku_id={urllib.parse.quote(studio_sku_id)}"
        f"&user_id={urllib.parse.quote(uid)}"
    )
    cancel_url = f"{base}/shop?paypal=cancel"
    try:
        from backend.services.paypal_service import create_order

        result = create_order(
            amount=price,
            currency=str(sku.get("currency") or "USD"),
            item_name=str(sku.get("label") or studio_sku_id),
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={
                "item_id": item_id,
                "user_id": uid,
                "product": "scr_deposit",
                "studio_sku_id": studio_sku_id,
                "org_label": (org_label or "").strip(),
            },
        )
    except Exception as e:
        return {"success": False, "error": str(e)}
    if not result.get("success"):
        return result
    return {
        "success": True,
        "order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "studio_sku_id": studio_sku_id,
        "amount_usd": price,
        "item_id": item_id,
    }


def fulfill_scr_capture(
    *,
    user_id: str,
    order_id: str,
    capture_id: Optional[str],
    amount_usd: float,
    studio_sku_id: str,
    org_label: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services.monetization_config_service import get_b2b_studio_sku
    from backend.services.monetization_ledger_service import append_payment_event

    sku = get_b2b_studio_sku(studio_sku_id)
    pool = float(sku.get("generation_credits_pool") or 0) if sku else 0.0
    append_payment_event(
        provider="paypal",
        user_id=user_id,
        order_id=order_id,
        capture_id=capture_id,
        amount_usd=float(amount_usd),
        currency="USD",
        item_id=f"scr-{studio_sku_id}",
        item_name=str((sku or {}).get("label") or studio_sku_id),
        generation_credits_granted=pool,
        deal_kind="scr_deposit",
        org_label=org_label,
        studio_sku_id=studio_sku_id,
        extra={"self_serve": True},
    )
    return {
        "success": True,
        "studio_sku_id": studio_sku_id,
        "generation_credits_pool": pool,
        "org_label": org_label,
    }
