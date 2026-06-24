"""Discord API routes — link, digest, status."""
from __future__ import annotations

import json
import os
from flask import Blueprint, jsonify, request, redirect

discord_bp = Blueprint("discord", __name__)
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")


def _ops_ok() -> bool:
    secrets = [
        os.environ.get("DISCORD_OPS_SECRET"),
        os.environ.get("MN2_OPS_SECRET"),
        os.environ.get("ADMIN_OPS_SECRET"),
    ]
    secrets = [s.strip() for s in secrets if s and str(s).strip()]
    if not secrets:
        return False
    hdr = request.headers.get("X-Ops-Secret") or request.args.get("ops_secret")
    return hdr in secrets


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


@discord_bp.route("/api/discord/mn2/config", methods=["GET"])
def discord_mn2_config():
    from backend.services.discord_mn2_channel_service import get_config, resolve_webhook

    cfg = get_config()
    cfg["webhook_resolved"] = bool(resolve_webhook())
    return jsonify({"success": True, **cfg}), 200


@discord_bp.route("/api/discord/mn2/digest/run", methods=["POST"])
def discord_mn2_digest_run():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    force = request.args.get("force") == "1" or (request.get_json(silent=True) or {}).get("force")
    from backend.services.discord_m8_streams import run_mn2_channel_digest
    result = run_mn2_channel_digest(force=bool(force))
    return jsonify(result), 200


def _controller_auth_ok() -> bool:
    secret = (os.environ.get("DISCORD_CONTROLLER_SECRET") or os.environ.get("DISCORD_OPS_SECRET") or "").strip()
    if not secret:
        return False
    return request.headers.get("X-Discord-Controller-Secret") == secret or request.headers.get("X-Ops-Secret") == secret


@discord_bp.route("/api/discord/app/manifest", methods=["GET"])
def discord_app_manifest():
    from backend.services.discord_controller_service import get_app_manifest
    return jsonify(get_app_manifest()), 200


@discord_bp.route("/api/discord/controller/status", methods=["GET"])
def discord_controller_status():
    user_id = (request.args.get("user_id") or "").strip() or None
    discord_id = (request.args.get("discord_id") or "").strip() or None
    from backend.services.discord_controller_service import get_controller_status
    return jsonify(get_controller_status(user_id=user_id, discord_id=discord_id)), 200


@discord_bp.route("/api/discord/controller/link-code", methods=["POST"])
def discord_controller_link_code():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.discord_controller_service import create_link_code
    out = create_link_code(user_id)
    return jsonify(out), 200 if out.get("success") else 400


@discord_bp.route("/api/discord/controller/link", methods=["POST"])
def discord_controller_link_complete():
    body = request.get_json(silent=True) or {}
    discord_id = (body.get("discord_id") or "").strip()
    code = (body.get("code") or "").strip()
    if not discord_id or not code:
        return jsonify({"success": False, "error": "discord_id and code required"}), 400
    from backend.services.discord_controller_service import complete_link_with_code
    out = complete_link_with_code(discord_id, code)
    return jsonify(out), 200 if out.get("success") else 400


@discord_bp.route("/api/discord/controller/daily-claim", methods=["POST"])
def discord_controller_daily_claim():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip() or None
    discord_id = (body.get("discord_id") or "").strip() or None
    from backend.services.discord_controller_service import claim_discord_daily
    out = claim_discord_daily(user_id=user_id, discord_id=discord_id)
    return jsonify(out), 200 if out.get("success") else 400


@discord_bp.route("/api/discord/controller/command", methods=["POST"])
def discord_controller_command():
    if not _controller_auth_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    command = (body.get("command") or body.get("name") or "").strip()
    discord_id = (body.get("discord_id") or "").strip()
    options = body.get("options") if isinstance(body.get("options"), dict) else {}
    from backend.services.discord_controller_service import handle_slash_command
    return jsonify(handle_slash_command(command, discord_id, options)), 200


@discord_bp.route("/api/discord/interactions", methods=["GET", "POST"], strict_slashes=False)
@discord_bp.route("/api/discord/interactions/", methods=["GET", "POST"])
def discord_interactions():
    """Discord Application Interactions endpoint (slash commands)."""
    if request.method == "GET":
        return jsonify({
            "success": True,
            "service": "discord_interactions",
            "interactions_url": "https://masternoder.dk/api/discord/interactions",
        }), 200
    raw = request.get_data()
    try:
        body = json.loads(raw.decode("utf-8") if raw else "{}")
    except Exception:
        return jsonify({"error": "invalid_json"}), 400
    if int(body.get("type") or 0) == 1:
        return jsonify({"type": 1}), 200
    pub = (os.environ.get("DISCORD_PUBLIC_KEY") or "").strip()
    if pub:
        from backend.services.discord_signature_service import verify_interaction_request
        ok, err = verify_interaction_request(request, public_key_hex=pub)
        if not ok:
            return jsonify({"error": err or "invalid_signature"}), 401
    elif not _controller_auth_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_controller_service import parse_discord_interaction
    resp = parse_discord_interaction(body)
    if resp is None:
        return jsonify({"type": 4, "data": {"content": "Unsupported interaction."}}), 200
    return jsonify(resp), 200


@discord_bp.route("/api/discord/setup/portal-urls", methods=["GET"])
def discord_setup_portal_urls():
    """Copy-paste URLs for Discord Developer Portal (Interactions, ToS, Privacy, Linked Roles)."""
    from backend.services.discord_role_connection_service import portal_urls
    from backend.services.discord_setup_service import validate_env_config

    return jsonify({
        "success": True,
        "urls": portal_urls(),
        "env": validate_env_config(),
        "bot_token_help": {
            "where": "Discord Developer Portal → Your App → Bot → Reset Token",
            "env_key": "DISCORD_BOT_TOKEN",
            "note": "Token is shown only once when created or reset.",
        },
    }), 200


@discord_bp.route("/api/discord/role-connection/start", methods=["GET"])
def discord_role_connection_start():
    from backend.services.discord_role_connection_service import build_authorize_url

    out = build_authorize_url()
    if not out.get("success"):
        return jsonify(out), 400
    return redirect(out["authorize_url"])


@discord_bp.route("/api/discord/role-connection/callback", methods=["GET"])
def discord_role_connection_callback():
    """Linked Roles Verification URL — also add to OAuth2 Redirects in Developer Portal."""
    import urllib.parse

    code = (request.args.get("code") or "").strip()
    if not code:
        from backend.services.discord_role_connection_service import portal_urls

        return jsonify({
            "success": True,
            "service": "discord_linked_roles_verification",
            "message": "Discord OAuth callback for Linked Roles. Users arrive here with ?code= after authorizing.",
            "urls": portal_urls(),
        }), 200
    from backend.services.discord_role_connection_service import handle_oauth_callback

    out = handle_oauth_callback(code)
    if out.get("success"):
        return redirect("/discord/verify/?verified=1")
    err = urllib.parse.quote(str(out.get("error") or "verify_failed")[:160])
    return redirect(f"/discord/verify/?error={err}")


@discord_bp.route("/api/discord/fanout/run", methods=["POST"])
def discord_fanout_run():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run"))
    channel = (body.get("channel") or "all").strip().lower()
    from backend.services.casino_discord_fanout import run_fanout as casino_fanout
    from backend.services.game_discord_fanout import run_fanout as game_fanout
    from backend.services.market_discord_fanout import run_fanout as market_fanout

    if channel == "casino":
        result = casino_fanout(dry_run=dry_run)
    elif channel == "market":
        result = market_fanout(dry_run=dry_run)
    elif channel == "game":
        result = game_fanout(dry_run=dry_run)
    else:
        from backend.services.social_platform_fanout_service import run_discord_fanouts
        result = run_discord_fanouts(dry_run=dry_run)
    return jsonify(result), 200


@discord_bp.route("/api/discord/market/fanout", methods=["POST"])
def discord_market_fanout():
    """Alias for cron scripts — market fills → #market."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.market_discord_fanout import run_fanout as market_fanout

    dry_run = bool((request.get_json(silent=True) or {}).get("dry_run"))
    return jsonify(market_fanout(dry_run=dry_run)), 200


@discord_bp.route("/api/discord/game/fanout", methods=["POST"])
def discord_game_fanout():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.game_discord_fanout import run_fanout as game_fanout

    dry_run = bool((request.get_json(silent=True) or {}).get("dry_run"))
    return jsonify(game_fanout(dry_run=dry_run)), 200


@discord_bp.route("/api/discord/casino/fanout", methods=["POST"])
def discord_casino_fanout():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.casino_discord_fanout import run_fanout as casino_fanout

    dry_run = bool((request.get_json(silent=True) or {}).get("dry_run"))
    return jsonify(casino_fanout(dry_run=dry_run)), 200


@discord_bp.route("/api/discord/m8/promo-rotator", methods=["POST"])
def discord_m8_promo_rotator():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_m8_streams import promo_rotator_payload

    return jsonify(promo_rotator_payload()), 200


@discord_bp.route("/api/discord/m8/alert-funnel", methods=["POST"])
def discord_m8_alert_funnel():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_m8_streams import run_alert_funnel

    return jsonify(run_alert_funnel()), 200


@discord_bp.route("/api/discord/setup/register-commands", methods=["POST"])
def discord_setup_register_commands():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_setup_service import register_global_commands

    return jsonify(register_global_commands()), 200
