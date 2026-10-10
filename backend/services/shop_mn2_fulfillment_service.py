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


_SHOP_FULFILLMENT_TYPES = frozenset({
    "shop_purchase",
    "shop_paypal_capture",
    "shop_mn2_purchase",
    "shop_monetization",
    "content_bundle",
    "digital_good",
    "mn2_pack",
})


def fulfillment_status_for_user(
    user_id: str,
    *,
    reference: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """Recent MN2 shop fulfillment rows + balance snapshot for UI status panels."""
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}

    lim = max(1, min(int(limit or 25), 100))
    ref_filter = (reference or "").strip() or None

    try:
        from backend.services.mn2_ledger import get_entries_by_user

        raw = get_entries_by_user(uid, limit=lim * 4)
    except Exception:
        raw = []

    fulfillments: list = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        etype = str(row.get("type") or "")
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        txid = str(row.get("txid") or "")
        if ref_filter and txid != ref_filter and ref_filter not in txid:
            continue
        is_shop = (
            etype in _SHOP_FULFILLMENT_TYPES
            or "shop" in etype.lower()
            or str(meta.get("purchase_source") or "").startswith("shop")
            or str(meta.get("source") or "").startswith("shop")
        )
        if not is_shop and not ref_filter:
            continue
        if ref_filter and not is_shop and txid != ref_filter:
            continue
        fulfillments.append({
            "reference": txid or None,
            "item_id": meta.get("item_id"),
            "item_name": meta.get("item_name"),
            "amount_mn2": round(float(row.get("amount") or 0), 8),
            "source": etype,
            "purchase_source": meta.get("purchase_source") or meta.get("source"),
            "quantity": meta.get("quantity"),
            "status": "credited",
            "created_at": row.get("created_at"),
        })
        if len(fulfillments) >= lim:
            break

    mn2_balance = 0.0
    try:
        from backend.services.unified_points_database import unified_points_db

        pts = unified_points_db.get_all_points(uid)
        p = pts.get("points") if isinstance(pts.get("points"), dict) else {}
        mn2_balance = float(p.get("mn2_balance") or 0)
    except Exception:
        pass

    pending_ref = ref_filter
    pending = bool(pending_ref and not fulfillments)

    return {
        "success": True,
        "user_id": uid,
        "mn2_balance": round(mn2_balance, 8),
        "fulfillment_count": len(fulfillments),
        "fulfillments": fulfillments,
        "reference": pending_ref,
        "pending": pending,
        "status": "pending" if pending else ("ok" if fulfillments else "none"),
    }
