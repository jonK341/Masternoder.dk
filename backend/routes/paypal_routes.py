"""
PayPal payment routes — create order, capture.
Integrates with shop and unified points.
Uses account resolution: session > request > user_identification.
"""
import urllib.parse
from flask import Blueprint, jsonify, request

paypal_bp = Blueprint("paypal", __name__)


def _resolve_user_id():
    """Resolve user_id from session, request, or identification."""
    from backend.services.account_resolution_service import resolve_user_id
    return resolve_user_id()


def _get_base_url():
    import os
    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    # Use origin only (no /vidgenerator) - return URL is built as base + /vidgenerator/shop
    if base.endswith("/vidgenerator"):
        base = base.rsplit("/vidgenerator", 1)[0]
    return base or request.url_root.rstrip("/")


@paypal_bp.route("/api/paypal/create-order", methods=["POST"])
def paypal_create_order():
    """Create PayPal order for shop item or coin pack."""
    data = request.get_json() or {}
    amount = float(data.get("amount", 0))
    item_id = data.get("item_id", "")
    item_name = data.get("item_name", "Shop Item")
    user_id = data.get("user_id") or _resolve_user_id()

    if amount <= 0:
        return jsonify({"success": False, "error": "Invalid amount"}), 400

    if not user_id or str(user_id).strip().lower() == "default_user":
        return jsonify({
            "success": False,
            "error": "Create an account first",
            "code": "ACCOUNT_REQUIRED",
            "message": "Please create or log in to an account in Profile before buying with PayPal.",
        }), 400

    from backend.services.account_security_service import check_purchase_action

    token = (data.get("verification_token") or data.get("security_token") or "").strip() or None
    sec_err = check_purchase_action(user_id, verification_token=token, price_usd=amount)
    if sec_err:
        return jsonify({
            "success": False,
            "error": sec_err,
            "code": "PASSWORD_VERIFICATION_REQUIRED",
            "requires_verification": True,
        }), 403

    base = _get_base_url()
    if not base:
        base = request.url_root.rstrip("/")
    return_url = f"{base}/shop?paypal=success&item_id={urllib.parse.quote(item_id)}&user_id={urllib.parse.quote(user_id)}"
    cancel_url = f"{base}/shop?paypal=cancel"

    try:
        from backend.services.paypal_service import create_order

        result = create_order(
            amount=amount,
            currency=data.get("currency", "USD"),
            item_name=item_name,
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": item_id, "user_id": user_id},
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    if result.get("success"):
        return jsonify({
            "success": True,
            "order_id": result["order_id"],
            "approve_url": result["approve_url"],
        }), 200
    return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500


@paypal_bp.route("/api/paypal/capture", methods=["POST"])
def paypal_capture():
    """Capture payment after user approves. Grant item and add monetization_points."""
    data = request.get_json() or {}
    order_id = data.get("order_id") or request.args.get("order_id")
    item_id = data.get("item_id", "")
    item_name = data.get("item_name", "")
    user_id = data.get("user_id") or _resolve_user_id()

    if not order_id:
        return jsonify({"success": False, "error": "Missing order_id"}), 400

    try:
        from backend.services.paypal_service import capture_order

        result = capture_order(order_id)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    if not result.get("success"):
        return jsonify({"success": False, "error": result.get("error", "Capture failed")}), 500

    amount = float(result.get("amount", 0) or 0)
    coins_granted = 0
    item_granted = None
    pack = None
    fulfillment_error = None

    try:
        from backend.services.unified_points_database import unified_points_db
        from backend.routes.shop_routes import get_coin_pack_map, _get_paypal_shop_items, _get_shop_items, _apply_shop_item_effects

        pack = get_coin_pack_map().get(item_id) if item_id else None
        paypal_items = _get_paypal_shop_items()
        shop_item = paypal_items.get(item_id) if item_id else None

        from backend.services.battle_pass_service import (
            fulfill_battle_pass_paypal_purchase,
            is_battle_pass_paypal_item,
        )

        if is_battle_pass_paypal_item(item_id):
            bp_out = fulfill_battle_pass_paypal_purchase(user_id)
            if bp_out.get("success"):
                item_granted = item_id
            else:
                fulfillment_error = bp_out.get("error") or "battle_pass_fulfillment_failed"
        elif pack and pack.get("coins_granted"):
            coins_granted = int(pack["coins_granted"])
            if unified_points_db and coins_granted > 0:
                unified_points_db.add_points(
                    user_id=user_id,
                    point_type="coins",
                    amount=coins_granted,
                    source="paypal",
                    metadata={
                        "order_id": order_id,
                        "capture_id": result.get("capture_id"),
                        "item_id": item_id,
                        "item_name": item_name or pack.get("name"),
                    },
                )
        elif shop_item:
            # Direct PayPal purchase: add item to inventory
            try:
                from backend.services.shop_db_service import fulfill_shop_purchase
                item_display_name = item_name or shop_item.get("name", item_id)
                purchase_id = fulfill_shop_purchase(
                    user_id=user_id,
                    item_id=item_id,
                    item_name=item_display_name,
                    quantity=1,
                    price_type="paypal",
                    price_paid_coins=0,
                    price_paid_points=None,
                )
                item_granted = item_id
                full_item = next((i for i in (_get_shop_items() or []) if (i.get("id") or "") == item_id), {"id": item_id, "name": item_display_name})
                _apply_shop_item_effects(user_id, item_id, full_item, 1)
            except Exception as e:
                fulfillment_error = str(e)
        elif unified_points_db and amount > 0:
            unified_points_db.add_points(
                user_id=user_id,
                point_type="monetization_points",
                amount=amount * 100,
                source="paypal",
                metadata={
                    "order_id": order_id,
                    "capture_id": result.get("capture_id"),
                    "item_id": item_id,
                    "item_name": item_name,
                },
            )
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('paypal')
        except Exception:
            pass
    except Exception:
        pass

    # Notify admin of purchase (email + log)
    try:
        from backend.services.purchase_notification_service import notify_purchase
        notify_purchase(
            amount=amount,
            currency=result.get("currency", "USD"),
            item_id=item_id,
            item_name=item_name,
            user_id=user_id,
            order_id=order_id,
            coins_granted=coins_granted,
            source="paypal",
        )
    except Exception:
        pass

    payload = {
        "success": True,
        "order_id": result["order_id"],
        "capture_id": result.get("capture_id"),
        "amount": result.get("amount"),
        "coins_granted": coins_granted,
    }
    if item_granted:
        payload["item_granted"] = item_granted
    if fulfillment_error:
        payload.update({
            "success": False,
            "payment_captured": True,
            "manual_fulfillment_required": True,
            "error": "PayPal payment captured, but item fulfillment failed",
            "details": fulfillment_error,
        })

    # Ledger for §0 phase C (gross margin vs revenue) — append-only JSONL
    try:
        from backend.services.monetization_ledger_service import append_payment_event

        gen_credits = 0.0
        if pack:
            try:
                gen_credits = float(pack.get("generation_credits_granted") or 0)
            except (TypeError, ValueError):
                gen_credits = 0.0
        ledger_name = (item_name or "").strip() or ((pack or {}).get("name") if pack else "") or ""
        append_payment_event(
            provider="paypal",
            user_id=user_id,
            order_id=order_id,
            capture_id=result.get("capture_id"),
            amount_usd=float(amount or 0),
            currency=str(result.get("currency") or "USD"),
            item_id=item_id or "",
            item_name=ledger_name,
            coins_granted=int(coins_granted or 0),
            generation_credits_granted=gen_credits,
        )
    except Exception:
        pass

    return jsonify(payload), 500 if fulfillment_error else 200
