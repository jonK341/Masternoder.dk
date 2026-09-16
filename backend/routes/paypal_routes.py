"""
PayPal payment routes — create order, capture.
Integrates with shop and unified points.
Uses account resolution: session > request > user_identification.

Trophy SKUs (plan 001 U2): server-priced create-order, idempotent capture, edition grant.
"""
import urllib.parse
from flask import Blueprint, jsonify, request

paypal_bp = Blueprint("paypal", __name__)

_ALLOWED_RETURN_SURFACES = frozenset({"shop", "exchange"})


def _resolve_user_id():
    """Resolve user_id from session, request, or identification."""
    from backend.services.account_resolution_service import resolve_user_id
    return resolve_user_id()


def _get_base_url():
    import os
    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    if base.endswith("/vidgenerator"):
        base = base.rsplit("/vidgenerator", 1)[0]
    return base or request.url_root.rstrip("/")


def _return_surface(data: dict) -> str:
    surface = (data.get("return_surface") or data.get("return_to") or "shop").strip().lower()
    if surface not in _ALLOWED_RETURN_SURFACES:
        surface = "shop"
    return surface


def _build_return_urls(base: str, surface: str, item_id: str, user_id: str) -> tuple:
    q = urllib.parse.urlencode({
        "paypal": "success",
        "item_id": item_id,
        "user_id": user_id,
    })
    if surface == "exchange":
        return f"{base}/exchange?{q}", f"{base}/exchange?paypal=cancel"
    return f"{base}/shop?{q}", f"{base}/shop?paypal=cancel"


def _trophy_purchase_name(item_name: str, item_id: str) -> str:
    label = (item_name or item_id or "Trophy").strip()
    return f"Licensed digital collectible trophy: {label}"


@paypal_bp.route("/api/paypal/create-order", methods=["POST"])
def paypal_create_order():
    """Create PayPal order for shop item, trophy, or coin pack."""
    data = request.get_json() or {}
    item_id = (data.get("item_id") or "").strip()
    item_name = data.get("item_name", "Shop Item")
    user_id = data.get("user_id") or _resolve_user_id()
    surface = _return_surface(data)

    if not user_id or str(user_id).strip().lower() == "default_user":
        return jsonify({
            "success": False,
            "error": "Create an account first",
            "code": "ACCOUNT_REQUIRED",
            "message": "Please create or log in to an account in Profile before buying with PayPal.",
        }), 400

    from backend.services.trophy_fulfillment_service import is_trophy_item

    trophy_checkout = bool(item_id and is_trophy_item(item_id))
    if trophy_checkout:
        from backend.services.trophy_pricing_service import get_effective_price

        pricing = get_effective_price(item_id)
        if not pricing.get("success"):
            return jsonify({
                "success": False,
                "error": pricing.get("error", "trophy_not_found"),
                "item_id": item_id,
            }), 404
        amount = float(pricing.get("effective_price_usd") or 0)
        item_name = _trophy_purchase_name(pricing.get("name") or item_name, item_id)
        if amount <= 0:
            return jsonify({"success": False, "error": "Invalid trophy price"}), 400
    else:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            return jsonify({"success": False, "error": "Invalid amount"}), 400

    base = _get_base_url()
    if not base:
        base = request.url_root.rstrip("/")
    return_url, cancel_url = _build_return_urls(base, surface, item_id, user_id)

    try:
        from backend.services.paypal_service import create_order

        result = create_order(
            amount=amount,
            currency=data.get("currency", "USD"),
            item_name=item_name,
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": item_id, "user_id": user_id, "kind": "trophy" if trophy_checkout else "shop"},
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    if result.get("success"):
        payload = {
            "success": True,
            "order_id": result["order_id"],
            "approve_url": result["approve_url"],
            "amount_usd": amount,
            "return_surface": surface,
        }
        if trophy_checkout:
            payload["kind"] = "trophy"
            payload["item_id"] = item_id
            payload["on_chain_mint"] = False
        return jsonify(payload), 200
    return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500


@paypal_bp.route("/api/paypal/capture", methods=["POST"])
def paypal_capture():
    """Capture payment after user approves. Grant item and add monetization_points."""
    data = request.get_json() or {}
    order_id = data.get("order_id") or request.args.get("order_id")
    item_id = (data.get("item_id") or "").strip()
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
    capture_id = result.get("capture_id") or order_id
    coins_granted = 0
    mn2_granted = 0.0
    item_granted = None
    pack = None
    mn2_pack = None
    fulfillment_error = None
    trophy_edition = None
    trophy_handled = False

    try:
        from backend.services.trophy_fulfillment_service import fulfill_trophy_paypal, is_trophy_item

        if item_id and is_trophy_item(item_id):
            trophy_handled = True
            grant = fulfill_trophy_paypal(
                user_id=user_id,
                item_id=item_id,
                item_name=item_name,
                order_id=order_id,
                capture_id=capture_id,
                amount_usd=amount,
            )
            if not grant.get("success"):
                fulfillment_error = grant.get("error") or "trophy_fulfillment_failed"
            else:
                item_granted = grant.get("item_granted") or item_id
                trophy_edition = grant.get("edition")
    except Exception as exc:
        fulfillment_error = str(exc)
        trophy_handled = True

    if not trophy_handled and not fulfillment_error and not item_granted:
        try:
            from backend.services.unified_points_database import unified_points_db
            from backend.routes.shop_routes import (
                get_coin_pack_map,
                get_mn2_pack_map,
                _get_paypal_shop_items,
                _get_shop_items,
                _apply_shop_item_effects,
            )

            pack = get_coin_pack_map().get(item_id) if item_id else None
            mn2_pack = get_mn2_pack_map().get(item_id) if item_id else None
            paypal_items = _get_paypal_shop_items()
            shop_item = paypal_items.get(item_id) if item_id else None

            if mn2_pack and float(mn2_pack.get("mn2_granted") or 0) > 0:
                from backend.services.shop_mn2_fulfillment_service import fulfill_mn2_purchase

                ref = f"paypal_mn2_pack:{capture_id}:{item_id}"
                grant = fulfill_mn2_purchase(
                    user_id,
                    item_id,
                    1,
                    source="paypal_mn2_pack",
                    reference=ref,
                    metadata={
                        "order_id": order_id,
                        "capture_id": capture_id,
                        "item_id": item_id,
                        "item_name": item_name or mn2_pack.get("name"),
                        "amount_usd": amount,
                    },
                    item=mn2_pack,
                )
                if grant.get("success") and not grant.get("skipped"):
                    mn2_granted = float(grant.get("mn2_granted") or 0)
                elif grant.get("skipped"):
                    fulfillment_error = "MN2 pack fulfillment skipped (no grant amount resolved)"
                else:
                    fulfillment_error = grant.get("error") or "MN2 pack fulfillment failed"
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
                            "capture_id": capture_id,
                            "item_id": item_id,
                            "item_name": item_name or pack.get("name"),
                        },
                    )
            elif shop_item:
                try:
                    from backend.services.shop_db_service import fulfill_shop_purchase

                    item_display_name = item_name or shop_item.get("name", item_id)
                    fulfill_shop_purchase(
                        user_id=user_id,
                        item_id=item_id,
                        item_name=item_display_name,
                        quantity=1,
                        price_type="paypal",
                        price_paid_coins=0,
                        price_paid_points=None,
                    )
                    item_granted = item_id
                    full_item = next(
                        (i for i in (_get_shop_items() or []) if (i.get("id") or "") == item_id),
                        {"id": item_id, "name": item_display_name},
                    )
                    _apply_shop_item_effects(user_id, item_id, full_item, 1, purchase_ref=capture_id)
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
                        "capture_id": capture_id,
                        "item_id": item_id,
                        "item_name": item_name,
                    },
                )
            try:
                from backend.services.unified_points_sync import unified_points_sync_device

                unified_points_sync_device.record_domain_sync("paypal")
            except Exception:
                pass
        except Exception:
            pass

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
        "capture_id": capture_id,
        "amount": result.get("amount"),
        "coins_granted": coins_granted,
        "mn2_granted": mn2_granted,
    }
    if item_granted:
        payload["item_granted"] = item_granted
    if trophy_edition:
        payload["trophy_edition"] = trophy_edition
        payload["edition_no"] = trophy_edition.get("edition_no")
        payload["edition_key"] = trophy_edition.get("edition_key")
        payload["on_chain_mint"] = False
    if fulfillment_error:
        payload.update({
            "success": False,
            "payment_captured": True,
            "manual_fulfillment_required": True,
            "error": "PayPal payment captured, but item fulfillment failed",
            "details": fulfillment_error,
        })

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
            capture_id=capture_id,
            amount_usd=float(amount or 0),
            currency=str(result.get("currency") or "USD"),
            item_id=item_id or "",
            item_name=ledger_name,
            coins_granted=int(coins_granted or 0),
            generation_credits_granted=gen_credits,
            extra={"kind": "trophy"} if trophy_edition else None,
        )
    except Exception:
        pass

    return jsonify(payload), 500 if fulfillment_error else 200


@paypal_bp.route("/api/paypal/trophy-webhook", methods=["POST"])
def paypal_trophy_webhook():
    """PayPal webhook: revoke trophy editions on dispute/chargeback (plan 001 Q6)."""
    try:
        body = request.get_json(silent=True) or {}
        from backend.services.paypal_webhook_service import verify_paypal_webhook_signature

        if not verify_paypal_webhook_signature(request.headers, body):
            return jsonify({"success": False, "error": "invalid_signature"}), 401

        from backend.services.trophy_paypal_webhook_service import process_trophy_paypal_webhook

        payload, status = process_trophy_paypal_webhook(body)
        return jsonify(payload), status
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
