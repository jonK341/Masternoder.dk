"""
PayPal payment routes — create order, capture, finish pending.
Integrates with shop and unified points.
Uses account resolution: session > request > user_identification.
"""
import os
import urllib.parse
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

paypal_bp = Blueprint("paypal", __name__)


def _resolve_user_id():
    """Resolve user_id from session, request, or identification."""
    from backend.services.account_resolution_service import resolve_user_id
    return resolve_user_id()


def _get_base_url():
    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    # Use origin only (no /vidgenerator) - return URL is built as base + /vidgenerator/shop
    if base.endswith("/vidgenerator"):
        base = base.rsplit("/vidgenerator", 1)[0]
    return base or request.url_root.rstrip("/")


def _ops_authorized() -> bool:
    secret = (
        (os.environ.get("PAYPAL_OPS_SECRET") or "").strip()
        or (os.environ.get("COGS_ADMIN_REPORT_KEY") or "").strip()
        or (os.environ.get("MN2_OPS_SECRET") or "").strip()
    )
    if not secret:
        flag = (os.environ.get("PAYPAL_FINISH_PENDING") or "").strip().lower()
        return flag in ("1", "true", "yes", "on")
    token = (
        request.headers.get("X-Ops-Token")
        or request.headers.get("X-Cogs-Admin-Key")
        or request.args.get("token")
        or request.args.get("key")
        or ""
    ).strip()
    body = request.get_json(silent=True) or {}
    if not token:
        token = str(body.get("token") or body.get("key") or "").strip()
    return token == secret


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

    base = _get_base_url()
    if not base:
        base = request.url_root.rstrip("/")
    return_url = f"{base}/shop?paypal=success&item_id={urllib.parse.quote(str(item_id))}&user_id={urllib.parse.quote(str(user_id))}"
    cancel_url = f"{base}/shop?paypal=cancel"

    try:
        from backend.services.paypal_service import create_order, remember_shop_order

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
        try:
            remember_shop_order(result.get("order_id"), {
                "status": "pending",
                "item_id": item_id,
                "item_name": item_name,
                "user_id": user_id,
                "amount": amount,
                "currency": data.get("currency", "USD"),
            })
        except Exception:
            pass
        return jsonify({
            "success": True,
            "order_id": result["order_id"],
            "approve_url": result["approve_url"],
        }), 200
    return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500


def fulfill_captured_shop_payment(
    *,
    order_id: str,
    user_id: str,
    item_id: str = "",
    item_name: str = "",
    capture: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Grant coins/items after a successful PayPal capture. Idempotent on order_id."""
    from backend.services.paypal_service import (
        get_pending_shop_order,
        mark_shop_order_captured,
        update_shop_order,
    )

    capture = dict(capture or {})
    pending = get_pending_shop_order(order_id) or {}
    if pending.get("fulfilled"):
        payload = dict(pending.get("fulfillment") or {})
        payload.setdefault("success", True)
        payload.setdefault("already_fulfilled", True)
        payload.setdefault("order_id", order_id)
        return payload

    item_id = str(item_id or pending.get("item_id") or "").strip()
    item_name = str(item_name or pending.get("item_name") or "").strip()
    user_id = str(user_id or pending.get("user_id") or "").strip()

    amount = float(capture.get("amount", 0) or pending.get("amount") or 0)
    coins_granted = 0
    mn2_granted = 0.0
    item_granted = None
    pack = None
    mn2_pack = None
    fulfillment_error = None

    if not user_id:
        payload = {
            "success": True,
            "order_id": capture.get("order_id") or order_id,
            "capture_id": capture.get("capture_id"),
            "amount": capture.get("amount") if capture.get("amount") is not None else amount,
            "coins_granted": 0,
            "mn2_granted": 0.0,
            "already_captured": bool(capture.get("already_captured")),
            "fulfillment_skipped": True,
            "reason": "missing_user_id",
        }
        try:
            mark_shop_order_captured(order_id, capture.get("capture_id"))
            update_shop_order(order_id, fulfilled=False, fulfillment=payload)
        except Exception:
            pass
        return payload

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

            capture_id = capture.get("capture_id") or order_id
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
                        "capture_id": capture.get("capture_id"),
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
                _apply_shop_item_effects(
                    user_id, item_id, full_item, 1,
                    purchase_ref=capture.get("capture_id") or order_id,
                )
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
                    "capture_id": capture.get("capture_id"),
                    "item_id": item_id,
                    "item_name": item_name,
                },
            )
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync("paypal")
        except Exception:
            pass
    except Exception as e:
        fulfillment_error = fulfillment_error or str(e)

    try:
        from backend.services.purchase_notification_service import notify_purchase
        notify_purchase(
            amount=amount,
            currency=capture.get("currency", "USD"),
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
        "order_id": capture.get("order_id") or order_id,
        "capture_id": capture.get("capture_id"),
        "amount": capture.get("amount") if capture.get("amount") is not None else amount,
        "coins_granted": coins_granted,
        "mn2_granted": mn2_granted,
        "already_captured": bool(capture.get("already_captured")),
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
            capture_id=capture.get("capture_id"),
            amount_usd=float(amount or 0),
            currency=str(capture.get("currency") or "USD"),
            item_id=item_id or "",
            item_name=ledger_name,
            coins_granted=int(coins_granted or 0),
            generation_credits_granted=gen_credits,
        )
    except Exception:
        pass

    try:
        mark_shop_order_captured(order_id, capture.get("capture_id"))
        update_shop_order(
            order_id,
            fulfilled=not bool(fulfillment_error),
            fulfillment=payload,
            user_id=user_id,
            item_id=item_id,
            item_name=item_name,
        )
    except Exception:
        pass

    return payload


@paypal_bp.route("/api/paypal/capture", methods=["POST"])
def paypal_capture():
    """Capture payment after user approves. Grant item and add monetization_points."""
    data = request.get_json() or {}
    order_id = data.get("order_id") or request.args.get("order_id") or request.args.get("token")
    item_id = data.get("item_id", "")
    item_name = data.get("item_name", "")
    user_id = data.get("user_id") or _resolve_user_id()

    if not order_id:
        return jsonify({"success": False, "error": "Missing order_id"}), 400

    try:
        from backend.services.paypal_service import capture_order, get_pending_shop_order

        pending = get_pending_shop_order(order_id) or {}
        item_id = item_id or pending.get("item_id") or ""
        item_name = item_name or pending.get("item_name") or ""
        resolved = str(user_id or "").strip()
        if not resolved or resolved.lower() == "default_user":
            user_id = pending.get("user_id") or user_id
        result = capture_order(order_id)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    if not result.get("success"):
        return jsonify({"success": False, "error": result.get("error", "Capture failed")}), 500

    payload = fulfill_captured_shop_payment(
        order_id=order_id,
        user_id=user_id,
        item_id=item_id,
        item_name=item_name,
        capture=result,
    )
    return jsonify(payload), 500 if payload.get("fulfillment_error") or (
        payload.get("manual_fulfillment_required") and not payload.get("success")
    ) else 200


@paypal_bp.route("/api/paypal/ops/pending", methods=["GET"])
def paypal_ops_pending():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    from backend.services.paypal_order_events import collect_pending_paypal_jobs

    jobs = collect_pending_paypal_jobs()
    return jsonify({"success": True, "pending": len(jobs), "orders": jobs}), 200


@paypal_bp.route("/api/paypal/ops/finish-pending", methods=["POST", "GET"])
def paypal_ops_finish_pending():
    """Capture APPROVED PayPal checkouts so funds settle, then fulfill the matching rail."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    extra = data.get("order_ids") or request.args.getlist("order_id")
    if isinstance(extra, str):
        extra = [part.strip() for part in extra.split(",") if part.strip()]
    try:
        limit = int(data.get("limit") or request.args.get("limit") or 400)
    except (TypeError, ValueError):
        limit = 400
    dry_run = bool(data.get("dry_run")) or request.args.get("dry_run") in ("1", "true", "yes")
    from backend.services.paypal_order_events import finish_pending_paypal_orders

    result = finish_pending_paypal_orders(
        limit=limit,
        extra_order_ids=list(extra or []),
        dry_run=dry_run,
    )
    return jsonify(result), 200


@paypal_bp.route("/vidgenerator/api/paypal/create-order", methods=["POST"])
def paypal_create_order_vid():
    return paypal_create_order()


@paypal_bp.route("/vidgenerator/api/paypal/capture", methods=["POST"])
def paypal_capture_vid():
    return paypal_capture()
