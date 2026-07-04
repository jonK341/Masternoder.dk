"""
Shared MN2 in-wallet shop purchase (Catalog + agents).
Lazy-imports shop_routes helpers to avoid import cycles.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple


def purchase_with_mn2_balance(
    user_id: str,
    item_id: str,
    quantity: int = 1,
    *,
    agent_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Perform MN2 balance purchase for a coin-priced item.
    Returns (response_body_dict, http_status).
    """
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    qty = max(1, int(quantity or 1))
    if not uid or not iid:
        return {"success": False, "error": "user_id and item_id required"}, 400

    from backend.routes.shop_routes import _get_shop_items, _apply_shop_item_effects

    all_items = _get_shop_items()
    item = next((i for i in all_items or [] if (i.get("id") or "") == iid), None)
    if not item:
        return {"success": False, "error": f"Item {iid} not found"}, 404

    item_price = item.get("price", 0)
    if isinstance(item_price, dict):
        return {"success": False, "error": "MN2 purchase only for coin-priced items"}, 400

    total_cost = int(item_price) * qty
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg_path = os.path.join(base, "data", "mn2_config.json")
    coins_per_mn2 = 100.0
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                coins_per_mn2 = float(cfg.get("coins_per_mn2") or 100)
        except Exception:
            pass
    if coins_per_mn2 <= 0:
        return {"success": False, "error": "MN2 price not configured"}, 400
    price_mn2 = total_cost / coins_per_mn2

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    points_result = unified_points_db.get_all_points(uid)
    if not points_result.get("success"):
        return {"success": False, "error": "Failed to retrieve user points"}, 500
    user_points = points_result.get("points", {})
    mn2_balance = float(user_points.get("mn2_balance", 0) or 0)
    if mn2_balance == 0 and isinstance(user_points.get("systems"), dict):
        mn2_balance = float(user_points["systems"].get("mn2_balance", 0) or 0)

    if mn2_balance < price_mn2:
        return {
            "success": False,
            "error": f"Insufficient MN2 balance. Need {price_mn2:.8f} MN2, have {mn2_balance:.8f}",
            "price_mn2": price_mn2,
            "mn2_balance": mn2_balance,
        }, 400

    meta = {"item_id": iid, "item_name": item.get("name"), "quantity": qty, "price_coins": total_cost}
    if agent_id:
        meta["agent_id"] = agent_id
        meta["source"] = "agent_mn2_shop"

    debit_result = unified_points_db.add_points(
        user_id=uid,
        point_type="mn2_balance",
        amount=-price_mn2,
        source="mn2_shop_purchase" if not agent_id else "agent_mn2_shop_purchase",
        metadata=meta,
    )
    if not debit_result.get("success", True):
        return {"success": False, "error": "Failed to debit MN2 balance"}, 500
    balance_after_mn2 = unified_points_db.get_all_points(uid).get("points", {})

    purchase_id = None
    try:
        from backend.services.shop_db_service import fulfill_shop_purchase

        purchase_id = fulfill_shop_purchase(
            user_id=uid,
            item_id=iid,
            item_name=item.get("name", ""),
            quantity=qty,
            price_type="mn2",
            price_paid_coins=0,
            price_paid_points={"mn2": price_mn2},
            balance_before=user_points,
            balance_after=balance_after_mn2,
        )
    except Exception as ex:
        refund_result = unified_points_db.add_points(
            user_id=uid,
            point_type="mn2_balance",
            amount=price_mn2,
            source="mn2_shop_purchase_refund",
            metadata={**meta, "reason": "fulfillment_failed", "error": str(ex)},
        )
        try:
            append_entry(
                user_id=uid,
                entry_type="shop_refund",
                amount=price_mn2,
                txid=None,
                address=None,
                metadata={**meta, "reason": "fulfillment_failed", "error": str(ex)},
            )
        except Exception:
            pass
        return {
            "success": False,
            "error": "MN2 was not charged because shop fulfillment failed" if refund_result.get("success", True) else "Shop fulfillment failed after MN2 debit; refund failed",
            "refund_applied": bool(refund_result.get("success", True)),
            "details": str(ex),
        }, 500

    append_entry(
        user_id=uid,
        entry_type="shop_payment",
        amount=price_mn2,
        txid=None,
        address=None,
        metadata=meta,
    )

    _apply_shop_item_effects(uid, iid, item, qty, purchase_ref=str(purchase_id) if purchase_id else None)

    # Shop V9.2: loyalty/cashback on the coin-equivalent value of MN2 spend.
    loyalty_earned = 0
    try:
        from backend.services.shop_monetization_service import accrue_purchase_loyalty

        loyalty_earned = int((accrue_purchase_loyalty(uid, total_cost) or {}).get("earned") or 0)
    except Exception:
        loyalty_earned = 0

    try:
        from backend.services.unified_points_sync import unified_points_sync_device

        unified_points_sync_device.record_domain_sync("shop")
    except Exception:
        pass

    if agent_id:
        try:
            from backend.services.agent_db_service import agent_db_service

            agent_db_service.record_agent_activity(
                user_id=uid,
                agent_id=agent_id,
                action="shop_purchase_mn2",
                skill="shop_purchase",
                xp_gained=10,
                points_gained=0,
                metadata={"item_id": iid, "item_name": item.get("name"), "quantity": qty, "mn2": price_mn2},
            )
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Purchased {qty}x {item.get('name')} with MN2",
        "item": item,
        "item_id": iid,
        "user_id": uid,
        "quantity": qty,
        "payment_method": "mn2",
        "price_paid_mn2": price_mn2,
        "price_coins_equivalent": total_cost,
        "loyalty_earned": loyalty_earned,
        "purchase_id": purchase_id,
        "agent_id": agent_id,
    }, 200
