"""Facebook Messenger casino webhook + status (MN2 E3 distribution stream)."""
from __future__ import annotations

import json

from flask import Blueprint, jsonify, request

facebook_casino_bp = Blueprint("facebook_casino", __name__)


@facebook_casino_bp.route("/api/facebook/casino/status", methods=["GET"])
def facebook_casino_status():
    from backend.services.facebook_casino_bot_service import public_status

    return jsonify(public_status()), 200


@facebook_casino_bp.route("/api/facebook/casino/webhook", methods=["GET"])
def facebook_casino_webhook_verify():
    from backend.services.facebook_casino_bot_service import verify_webhook

    mode = request.args.get("hub.mode") or ""
    token = request.args.get("hub.verify_token") or ""
    challenge = request.args.get("hub.challenge") or ""
    result = verify_webhook(mode, token, challenge)
    if result is None:
        return jsonify({"success": False, "error": "verification_failed"}), 403
    return result, 200, {"Content-Type": "text/plain"}


@facebook_casino_bp.route("/api/facebook/casino/webhook", methods=["POST"])
def facebook_casino_webhook_events():
    from backend.services.facebook_casino_bot_service import handle_webhook_payload, verify_signature

    raw_body = request.get_data()
    ok, err = verify_signature(raw_body, request.headers.get("X-Hub-Signature-256") or "")
    if not ok:
        return jsonify({"success": False, "error": err}), 401
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "invalid_json"}), 400
    result = handle_webhook_payload(payload)
    return jsonify(result), 200
