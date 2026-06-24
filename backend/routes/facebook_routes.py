"""Facebook Casino Bot — Messenger webhook + casino link APIs."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

facebook_bp = Blueprint("facebook_casino", __name__)


def _webhook_auth_ok() -> bool:
    secret = (os.environ.get("FACEBOOK_APP_SECRET") or os.environ.get("FACEBOOK_OPS_SECRET") or "").strip()
    if not secret:
        return True
    return request.headers.get("X-Facebook-Ops-Secret") == secret


@facebook_bp.route("/api/facebook/casino/config", methods=["GET"])
def facebook_casino_config():
    from backend.services.facebook_casino_bot_service import get_bot_config
    return jsonify(get_bot_config()), 200


@facebook_bp.route("/api/facebook/casino/status", methods=["GET"])
def facebook_casino_status():
    user_id = (request.args.get("user_id") or "").strip() or None
    psid = (request.args.get("facebook_psid") or "").strip() or None
    from backend.services.facebook_casino_bot_service import get_facebook_status
    return jsonify(get_facebook_status(user_id=user_id, facebook_psid=psid)), 200


@facebook_bp.route("/api/facebook/casino/link-code", methods=["POST"])
def facebook_casino_link_code():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.facebook_casino_bot_service import create_link_code
    out = create_link_code(user_id)
    return jsonify(out), 200 if out.get("success") else 400


@facebook_bp.route("/api/facebook/casino/link", methods=["POST"])
def facebook_casino_link():
    body = request.get_json(silent=True) or {}
    psid = (body.get("facebook_psid") or "").strip()
    code = (body.get("code") or "").strip()
    if not psid or not code:
        return jsonify({"success": False, "error": "facebook_psid and code required"}), 400
    from backend.services.facebook_casino_bot_service import complete_link_with_code
    out = complete_link_with_code(psid, code)
    return jsonify(out), 200 if out.get("success") else 400


@facebook_bp.route("/api/facebook/casino/daily-claim", methods=["POST"])
def facebook_casino_daily_claim():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip() or None
    psid = (body.get("facebook_psid") or "").strip() or None
    from backend.services.facebook_casino_bot_service import claim_facebook_daily
    out = claim_facebook_daily(user_id=user_id, facebook_psid=psid)
    return jsonify(out), 200 if out.get("success") else 400


@facebook_bp.route("/api/facebook/casino/webhook", methods=["GET", "POST"])
def facebook_casino_webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode", "")
        token = request.args.get("hub.verify_token", "")
        challenge = request.args.get("hub.challenge", "")
        from backend.services.facebook_casino_bot_service import verify_webhook
        result = verify_webhook(mode, token, challenge)
        if result is not None:
            return result, 200
        return "Forbidden", 403
    if not _webhook_auth_ok():
        return jsonify({"error": "unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    from backend.services.facebook_casino_bot_service import process_webhook
    return jsonify(process_webhook(body)), 200


@facebook_bp.route("/api/facebook/casino/message", methods=["POST"])
def facebook_casino_message_test():
    """Dev/test endpoint — simulate Messenger text."""
    if not _webhook_auth_ok() and os.environ.get("FACEBOOK_APP_SECRET"):
        return jsonify({"error": "unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    psid = (body.get("facebook_psid") or body.get("psid") or "").strip()
    text = (body.get("text") or "").strip()
    if not psid or not text:
        return jsonify({"success": False, "error": "facebook_psid and text required"}), 400
    from backend.services.facebook_casino_bot_service import handle_messenger_text
    return jsonify(handle_messenger_text(psid, text)), 200
