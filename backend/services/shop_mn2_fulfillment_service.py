"""
Automatic MN2 delivery when users purchase MN2 packs or SKUs with mn2_granted.

Wired from shop coin/MN2 checkout, PayPal capture, bundle/digital-good effects,
and shop monetization rewards (mystery box / spin wheel grants).
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _pack_map() -> Dict[str, Dict[str, Any]]:
    try:
        from backend.services.monetization_config_service import get_mn2_pack_map

        return get_mn2_pack_map()
    except Exception:
        return {}


def mn2_granted_for_item(item_id: str, item: Optional[Dict[str, Any]] = None, quantity: int = 1) -> float:
    """Return total MN2 to credit for a catalog SKU (0 if not an MN2 grant SKU)."""
    iid = (item_id or "").strip()
    qty = max(1, int(quantity or 1))

    row = item if isinstance(item, dict) else {}
    if row.get("mn2_granted") is not None:
        try:
            return round(float(row.get("mn2_granted") or 0) * qty, 8)
        except (TypeError, ValueError):
            pass

    pack = _pack_map().get(iid)
    if pack:
        return round(float(pack.get("mn2_granted") or 0) * qty, 8)

    if not row and iid:
        try:
            from backend.routes.shop_routes import _content_bundle_by_id, _digital_good_by_id

            row = _content_bundle_by_id(iid) or _digital_good_by_id(iid) or {}
        except Exception:
            row = {}

    raw = row.get("mn2_granted")
    if raw is None:
        return 0.0
    try:
        return round(float(raw) * qty, 8)
    except (TypeError, ValueError):
        return 0.0


def fulfill_mn2_purchase(
    user_id: str,
    item_id: str,
    quantity: int = 1,
    *,
    source: str,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
    item: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Credit MN2 for a qualifying purchase. Idempotent on ``reference`` via game_mn2_rewards.
    Returns {success, mn2_granted, skipped?, duplicate?, error?}.
    """
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    if not uid or not iid:
        return {"success": False, "error": "user_id and item_id required"}

    mn2_amount = mn2_granted_for_item(iid, item=item, quantity=quantity)
    if mn2_amount <= 0:
        return {"success": True, "skipped": True, "mn2_granted": 0.0}

    ref = (reference or "").strip() or f"{source}:{iid}"
    meta = dict(metadata or {})
    meta.update({"item_id": iid, "quantity": max(1, int(quantity or 1)), "purchase_source": source})

    from backend.services.game_mn2_rewards import credit_mn2

    result = credit_mn2(uid, mn2_amount, source=source, reference=ref, metadata=meta)
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "MN2 credit failed"), "mn2_granted": 0.0}
    return {
        "success": True,
        "mn2_granted": float(result.get("amount") or mn2_amount),
        "duplicate": bool(result.get("duplicate")),
        "user_id": uid,
        "item_id": iid,
    }


def apply_mn2_grants_for_purchase(
    user_id: str,
    item_id: str,
    item: Optional[Dict[str, Any]],
    quantity: int,
    *,
    source: str = "shop_purchase",
    reference: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Best-effort MN2 grant hook for shop item effects (never raises)."""
    try:
        ref = reference or f"{source}:{item_id}:{max(1, int(quantity or 1))}"
        return fulfill_mn2_purchase(
            user_id,
            item_id,
            quantity,
            source=source,
            reference=ref,
            metadata=extra_metadata,
            item=item,
        )
    except Exception as ex:
        return {"success": False, "error": str(ex), "mn2_granted": 0.0}
