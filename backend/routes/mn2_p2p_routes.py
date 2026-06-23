"""
MN2 P2P marketplace API routes (Model B, guarded - disabled by default).

Seller escrows MN2 and lists it; buyer pays USD via PayPal; escrow releases to buyer
under a hold; seller payout releases after the buyer's chargeback window clears.
See docs/MN2_STAKING_PLAN.md sec.17 and backend/services/mn2_p2p_service.py.
"""
import os
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
import backend.services.mn2_p2p_service as p2p

mn2_p2p_bp = Blueprint("mn2_p2p", __name__)


def _ops_authorized() -> bool:
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (request.headers.get("X-Ops-Token") or request.headers.get("X-Scanner-Token")
             or request.args.get("token") or "").strip()
    return token == secret


def _body() -> dict:
    return request.get_json(silent=True) or {}


@mn2_p2p_bp.route("/api/mn2/p2p/oracle", methods=["GET"])
def p2p_oracle():
    try:
        from backend.services.mn2_p2p_oracle import get_corridor
        return jsonify(get_corridor()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/config", methods=["GET"])
def p2p_config():
    try:
        cfg = p2p.get_config()
        return jsonify({
            "success": True,
            "enabled": cfg.get("enabled"),
            "platform_fee_percent": cfg.get("platform_fee_percent"),
            "buyer_spread_percent": cfg.get("buyer_spread_percent"),
            "min_listing_mn2": cfg.get("min_listing_mn2"),
            "max_listing_mn2": cfg.get("max_listing_mn2"),
            "hold_hours": cfg.get("hold_hours"),
            "requires_seller_verification": cfg.get("requires_seller_verification"),
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/listings", methods=["GET"])
def p2p_listings():
    try:
        return jsonify(p2p.list_listings(limit=int(request.args.get("limit", 100)))), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/listings", methods=["POST"])
def p2p_create_listing():
    try:
        data = _body()
        seller_id = resolve_user_id(from_body=True, from_query=True)
        result = p2p.create_listing(seller_id, data.get("mn2_amount"), data.get("price_usd_per_mn2"))
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/listings/cancel", methods=["POST"])
def p2p_cancel_listing():
    try:
        data = _body()
        seller_id = resolve_user_id(from_body=True, from_query=True)
        result = p2p.cancel_listing(seller_id, (data.get("listing_id") or "").strip())
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/buy", methods=["POST"])
def p2p_buy():
    try:
        data = _body()
        buyer_id = resolve_user_id(from_body=True, from_query=True)
        result = p2p.create_purchase(
            buyer_id,
            (data.get("listing_id") or "").strip(),
            mn2_amount=data.get("mn2_amount"),
            return_url=data.get("return_url"),
            cancel_url=data.get("cancel_url"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/capture", methods=["POST"])
def p2p_capture():
    try:
        data = _body()
        buyer_id = resolve_user_id(from_body=True, from_query=True)
        result = p2p.capture((data.get("order_id") or "").strip(), buyer_id)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/status", methods=["GET"])
def p2p_status():
    try:
        user_id = resolve_user_id(from_body=False, from_query=True)
        order_id = (request.args.get("order_id") or "").strip()
        if order_id:
            return jsonify(p2p.get_order(order_id, user_id)), 200
        return jsonify(p2p.get_user_overview(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/webhook", methods=["POST"])
def p2p_webhook():
    try:
        event = request.get_json(silent=True) or {}
        try:
            from backend.services.paypal_webhook_service import verify_paypal_webhook_signature
            signature_ok = verify_paypal_webhook_signature(request.headers, event)
        except Exception:
            signature_ok = False
        event_key = ""
        try:
            resource = event.get("resource") or {}
            event_key = str(resource.get("id") or event.get("id") or "")
        except Exception:
            pass
        try:
            from backend.services.webhook_outbox import process_inline
            result = process_inline(
                "p2p_paypal",
                event_key or "unknown",
                {"event": event, "signature_ok": signature_ok},
                handler="p2p_paypal",
            )
        except ImportError:
            result = p2p.handle_webhook(event, signature_ok)
        if isinstance(result, dict) and result.get("error") == "Webhook signature not verified":
            return jsonify(result), 400
        return jsonify(result if isinstance(result, dict) else {"success": True}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_p2p_bp.route("/api/mn2/p2p/ops/clear-matured", methods=["POST", "GET"])
def p2p_clear_matured():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        return jsonify(p2p.clear_matured()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
