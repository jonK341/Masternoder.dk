"""Discord API routes — link, digest, status."""
from __future__ import annotations

import json
import os
from flask import Blueprint, jsonify, request

discord_bp = Blueprint("discord", __name__)
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")


def _ops_ok() -> bool:
    secret = os.environ.get("DISCORD_OPS_SECRET", "")
    if not secret:
        return False
    return request.headers.get("X-Ops-Secret") == secret or request.args.get("ops_secret") == secret


@discord_bp.route("/api/discord/status", methods=["GET"])
def discord_status():
    from backend.services.discord_service import recent_outbox
    rows = recent_outbox(5)
    last = rows[0] if rows else None
    return jsonify({
        "success": True,
        "webhook_configured": bool(os.environ.get("DISCORD_WEBHOOK_URL")),
        "last_post": last,
        "recent_failures": sum(1 for r in rows if not r.get("success")),
    }), 200


@discord_bp.route("/api/discord/post", methods=["POST"])
def discord_post():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    channel = (body.get("channel") or "ops").strip()
    from backend.services.discord_service import post_message
    result = post_message(channel, body.get("payload") or body, message_id=body.get("message_id"))
    return jsonify(result), 200 if result.get("success") else 502


@discord_bp.route("/api/discord/digest/run", methods=["POST"])
def discord_digest_run():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.platform_news_digest import run_daily_digest
    result = run_daily_digest()
    return jsonify(result), 200


@discord_bp.route("/api/discord/casino/fanout", methods=["POST"])
def discord_casino_fanout():
    """Cron entry — casino activity_events → #casino (alias of /api/casino/discord/notify)."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services import casino_discord_fanout
    data = request.get_json(silent=True) or {}
    result = casino_discord_fanout.run_fanout(dry_run=bool(data.get("dry_run")))
    return jsonify(result), 200


@discord_bp.route("/api/discord/link", methods=["POST"])
def discord_link():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    discord_id = (body.get("discord_id") or body.get("discord_user_id") or "").strip()
    if not user_id or not discord_id:
        return jsonify({"success": False, "error": "user_id and discord_id required"}), 400
    os.makedirs(_IDENT_DIR, exist_ok=True)
    path = os.path.join(_IDENT_DIR, f"discord_{discord_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"user_id": user_id, "discord_id": discord_id, "linked": True}, f, indent=2)
    return jsonify({"success": True, "user_id": user_id, "discord_id": discord_id}), 200


@discord_bp.route("/api/ai/staking-advisor", methods=["GET"])
def staking_advisor_get():
    user_id = request.args.get("user_id", "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.ai_staking_advisor_service import get_advice
    return jsonify(get_advice(user_id)), 200


@discord_bp.route("/api/ai/staking-advisor/refresh", methods=["POST"])
def staking_advisor_refresh():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.ai_staking_advisor_service import refresh_advice
    return jsonify(refresh_advice(user_id)), 200
