"""
PayPal -> MN2 on-ramp API routes (Model A, custodial).

Quote -> create PayPal order -> capture (client confirm) / webhook -> hold -> clear.
See docs/MN2_STAKING_PLAN.md sec.17 and backend/services/mn2_onramp_service.py.
"""
import os
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
import backend.services.mn2_onramp_service as onramp

mn2_onramp_bp = Blueprint("mn2_onramp", __name__)


def _ops_authorized() -> bool:
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (request.headers.get("X-Ops-Token") or request.headers.get("X-Scanner-Token")
             or request.args.get("token") or "").strip()
    return token == secret


def _body() -> dict:
    return request.get_json(silent=True) or {}


@mn2_onramp_bp.route("/api/mn2/onramp/config", methods=["GET"])
def onramp_config():
    try:
        cfg = onramp.get_config()
        return jsonify({
            "success": True,
            "enabled": cfg.get("enabled"),
            "model": cfg.get("model"),
            "spread_percent": cfg.get("spread_percent"),
            "quote_ttl_seconds": cfg.get("quote_ttl_seconds"),
            "hold_hours": cfg.get("hold_hours"),
            "min_usd": cfg.get("min_usd"),
            "max_usd_per_order": cfg.get("max_usd_per_order"),
            "daily_usd_cap": cfg.get("daily_usd_cap"),
            "daily_usd_cap_verified": cfg.get("daily_usd_cap_verified"),
            "lifetime_usd_cap_unverified": cfg.get("lifetime_usd_cap_unverified"),
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_onramp_bp.route("/api/mn2/onramp/quote", methods=["GET", "POST"])
def onramp_quote():
    try:
        user_id = resolve_user_id(from_body=True, from_query=True)
        usd = _body().get("usd") if request.method == "POST" else request.args.get("usd")
        if usd is None:
            usd = request.args.get("usd")
        result = onramp.get_quote(usd, user_id)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_onramp_bp.route("/api/mn2/onramp/order", methods=["POST"])
def onramp_order():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        result = onramp.create_order(
            quote_id=(data.get("quote_id") or "").strip(),
            user_id=user_id,
            return_url=data.get("return_url"),
            cancel_url=data.get("cancel_url"),
        )
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_onramp_bp.route("/api/mn2/onramp/capture", methods=["POST"])
def onramp_capture():
    try:
        data = _body()
        user_id = resolve_user_id(from_body=True, from_query=True)
        order_id = (data.get("order_id") or "").strip()
        result = onramp.capture(order_id, user_id)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_onramp_bp.route("/api/mn2/onramp/status", methods=["GET"])
def onramp_status():
    try:
        user_id = resolve_user_id(from_body=False, from_query=True)
        order_id = (request.args.get("order_id") or "").strip()
        if order_id:
            return jsonify(onramp.get_status(order_id, user_id)), 200
        return jsonify(onramp.get_user_orders(user_id)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_onramp_bp.route("/api/mn2/onramp/webhook", methods=["POST"])
def onramp_webhook():
    try:
        event = request.get_json(silent=True) or {}
        try:
            from backend.services.paypal_webhook_service import verify_paypal_webhook_signature
            signature_ok = verify_paypal_webhook_signature(request.headers, event)
        except Exception:
            signature_ok = False
        result = onramp.handle_webhook(event, signature_ok)
        # Always 200 to PayPal on signature-verified handling; 400 only on bad signature
        if isinstance(result, dict) and result.get("error") == "Webhook signature not verified":
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@mn2_onramp_bp.route("/api/mn2/onramp/ops/clear-matured", methods=["POST", "GET"])
def onramp_clear_matured():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        return jsonify(onramp.clear_matured()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
