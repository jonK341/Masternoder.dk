"""Discord API routes — link, digest, status, interactions, linked roles."""
from __future__ import annotations

import json
import os
from flask import Blueprint, jsonify, redirect, request

discord_bp = Blueprint("discord", __name__)
_INTERACTION_PING = 1


def _discord_public_key_hex() -> str:
    """Portal Public Key from env (64 hex chars). Empty => signature verify skipped."""
    raw = (os.environ.get("DISCORD_PUBLIC_KEY") or "").strip().strip('"').strip("'")
    if raw.lower().startswith("0x"):
        raw = raw[2:]
    return "".join(raw.split())


def _verify_discord_signature(raw_body: bytes) -> tuple[bool, str | None]:
    """Verify Discord Ed25519 signature when DISCORD_PUBLIC_KEY is set."""
    public_key_hex = _discord_public_key_hex()
    if not public_key_hex:
        return True, None
    signature = (request.headers.get("X-Signature-Ed25519") or "").strip()
    timestamp = (request.headers.get("X-Signature-Timestamp") or "").strip()
    if not signature or not timestamp:
        return False, "missing_signature_headers"
    if len(public_key_hex) != 64:
        return False, "invalid_public_key_config"
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(bytes.fromhex(signature), timestamp.encode("utf-8") + raw_body)
        return True, None
    except Exception:
        return False, "invalid_signature"


def _ops_ok() -> bool:
    secret = os.environ.get("DISCORD_OPS_SECRET", "")
    if not secret:
        return False
    return request.headers.get("X-Ops-Secret") == secret or request.args.get("ops_secret") == secret


@discord_bp.route("/api/discord/interactions", methods=["POST"])
def discord_interactions():
    """Discord Interactions endpoint — PING/PONG for URL verification; verify sig when configured."""
    raw_body = request.get_data()
    ok, err = _verify_discord_signature(raw_body)
    if not ok:
        return jsonify({"success": False, "error": err}), 401
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "invalid_json"}), 400
    if payload.get("type") == _INTERACTION_PING:
        return jsonify({"type": 1}), 200
    return jsonify({"success": False, "error": "unsupported_interaction_type"}), 501


@discord_bp.route("/api/discord/status", methods=["GET"])
def discord_status():
    from backend.services.discord_service import recent_outbox
    rows = recent_outbox(5)
    last = rows[0] if rows else None
    public_key = _discord_public_key_hex()
    return jsonify({
        "success": True,
        "webhook_configured": bool(os.environ.get("DISCORD_WEBHOOK_URL")),
        "interactions_public_key_configured": bool(public_key),
        "interactions_public_key_valid_length": len(public_key) == 64 if public_key else False,
        "interactions_endpoint": "https://masternoder.dk/api/discord/interactions",
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


@discord_bp.route("/api/discord/link/status", methods=["GET"])
def discord_link_status():
    user_id = (request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.discord_link_service import link_status

    return jsonify(link_status(user_id)), 200


@discord_bp.route("/api/discord/link", methods=["POST"])
def discord_link():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    discord_id = (body.get("discord_id") or body.get("discord_user_id") or "").strip()
    if not user_id or not discord_id:
        return jsonify({"success": False, "error": "user_id and discord_id required"}), 400
    from backend.services.discord_link_service import link_user

    result = link_user(user_id, discord_id)
    return jsonify(result), 200 if result.get("success") else 400


@discord_bp.route("/api/discord/link/unlink", methods=["POST"])
def discord_link_unlink():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.discord_link_service import unlink_user

    result = unlink_user(user_id)
    return jsonify(result), 200 if result.get("success") else 400


@discord_bp.route("/api/discord/linked-role", methods=["GET"])
def discord_linked_role_start():
    """Linked Roles Verification URL — redirects to Discord OAuth (role_connections.write)."""
    from backend.services.discord_linked_roles_service import build_oauth_start

    user_id_hint = (request.args.get("user_id") or request.args.get("user_id_hint") or "").strip() or None
    result = build_oauth_start(user_id_hint=user_id_hint)
    if not result.get("success"):
        return jsonify(result), 503
    if (request.args.get("redirect") or "").lower() in ("0", "false", "no"):
        return jsonify(result), 200
    return redirect(result["auth_url"], code=302)


@discord_bp.route("/api/discord/linked-role/callback", methods=["GET"])
def discord_linked_role_callback():
    """OAuth redirect target after user approves linked-role scopes."""
    code = (request.args.get("code") or "").strip()
    state = (request.args.get("state") or "").strip()
    if not code or not state:
        return jsonify({"success": False, "error": "missing_code_or_state"}), 400
    from flask import session
    from backend.services.discord_linked_roles_service import handle_callback

    session_user = (session.get("user_id") or "").strip() or None
    if session_user == "default_user":
        session_user = None
    result = handle_callback(code, state, user_id_hint=session_user)
    if not result.get("success"):
        return jsonify(result), 400
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>MasterNoder Discord linked</title></head><body>"
        "<h1>Discord account connected</h1>"
        "<p>Your MasterNoder2 linked-role metadata was updated. "
        "Return to Discord to claim your linked role.</p>"
        "</body></html>"
    )
    return html, 200


@discord_bp.route("/api/discord/linked-role/register-metadata", methods=["POST"])
def discord_linked_role_register_metadata():
    """One-time ops call to register metadata schema with Discord (Bot token)."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_linked_roles_service import register_metadata_schema

    return jsonify(register_metadata_schema()), 200


@discord_bp.route("/api/discord/linked-role/schema", methods=["GET"])
def discord_linked_role_schema():
    from backend.services.discord_linked_roles_service import (
        configured,
        linked_role_redirect_uri,
        linked_role_verification_url,
        metadata_schema,
    )

    return jsonify(
        {
            "success": True,
            "verification_url": linked_role_verification_url(),
            "redirect_uri": linked_role_redirect_uri(),
            "oauth_configured": configured(),
            "metadata_schema": metadata_schema(),
        }
    ), 200


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
