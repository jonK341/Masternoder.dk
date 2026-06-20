"""Discord API routes — link, digest, status."""
from __future__ import annotations

import json
import os
from flask import Blueprint, jsonify, request

discord_bp = Blueprint("discord", __name__)
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")


def _ops_ok() -> bool:
    secret = (
        os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("MN2_SCAN_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("ADMIN_OPS_SECRET")
        or ""
    ).strip()
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return (
        request.headers.get("X-Ops-Secret") == secret
        or request.args.get("ops_secret") == secret
    )


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
    """Gate S cron — activity_events.jsonl → Discord #casino."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.casino_discord_fanout import run_fanout
    result = run_fanout(dry_run=bool(body.get("dry_run")))
    return jsonify(result), 200


@discord_bp.route("/api/discord/market/fanout", methods=["POST"])
def discord_market_fanout():
    """Gate S cron — market channel activity_events → Discord #market."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.market_discord_fanout import run_fanout
    result = run_fanout(dry_run=bool(body.get("dry_run")))
    return jsonify(result), 200


@discord_bp.route("/api/discord/casino/promo/create", methods=["POST"])
def discord_casino_promo_create():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services import casino_social_service
    promo = casino_social_service.create_discord_promo(
        reward_coins=int(body.get("reward_coins") or 50),
        max_redemptions=int(body.get("max_redemptions") or 100),
        ttl_hours=int(body.get("ttl_hours") or 48),
    )
    from backend.services.casino_discord_fanout import run_fanout
    run_fanout()
    return jsonify(promo), 200


@discord_bp.route("/api/discord/casino/vip-check", methods=["GET"])
def discord_casino_vip_check():
    user_id = (request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services import casino_social_service
    return jsonify(casino_social_service.check_vip_discord_eligibility(user_id)), 200


@discord_bp.route("/api/discord/hosting/vip-check", methods=["GET"])
def discord_hosting_vip_check():
    user_id = (request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.discord_hosting_vip_service import check_hosting_vip_eligibility

    return jsonify(check_hosting_vip_eligibility(user_id)), 200


@discord_bp.route("/api/discord/hosting/vip-sync", methods=["POST"])
def discord_hosting_vip_sync():
    data = request.get_json() or {}
    user_id = (data.get("user_id") or request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.discord_hosting_vip_service import grant_hosting_vip_role

    return jsonify(grant_hosting_vip_role(user_id, reason="manual_sync")), 200


@discord_bp.route("/api/discord/activity-funnel", methods=["POST"])
def discord_activity_funnel():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.activity_events_service import recent
    from backend.services.discord_service import post_message
    rows = recent(limit=20)
    summary = []
    for row in rows:
        summary.append(f"[{row.get('channel')}] {row.get('type')}: {row.get('text') or row.get('payload')}")
    body = "\n".join(summary[:15]) or "No recent activity"
    result = post_message("activity", {"content": f"**Activity funnel**\n{body}"}, message_id="activity-funnel")
    return jsonify({"success": result.get("success", False), "posted": len(summary)}), 200 if result.get("success") else 502


@discord_bp.route("/api/discord/m8/alert-funnel", methods=["POST"])
def discord_m8_alert_funnel():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_m8_streams import run_alert_funnel
    return jsonify(run_alert_funnel()), 200


@discord_bp.route("/api/discord/m8/partner-spotlight", methods=["POST"])
def discord_m8_partner_spotlight():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.discord_m8_streams import publish_partner_spotlight
    result = publish_partner_spotlight(
        title=(body.get("title") or "Partner update").strip(),
        summary=(body.get("summary") or "").strip(),
        href=(body.get("href") or "/shop/").strip(),
        partner_id=(body.get("partner_id") or body.get("id") or "").strip() or None,
    )
    return jsonify(result), 200 if result.get("success") else 502


@discord_bp.route("/api/discord/m8/quest-bot", methods=["POST"])
def discord_m8_quest_bot():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_m8_streams import run_quest_bot_digest
    return jsonify(run_quest_bot_digest()), 200


@discord_bp.route("/api/discord/m8/affiliate-rotator", methods=["POST"])
def discord_m8_affiliate_rotator():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_m8_streams import affiliate_rotator_payload
    return jsonify(affiliate_rotator_payload()), 200


@discord_bp.route("/api/discord/m8/promo-rotator", methods=["POST"])
def discord_m8_promo_rotator():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    from backend.services.discord_m8_streams import promo_rotator_payload
    return jsonify(promo_rotator_payload()), 200


@discord_bp.route("/api/discord/support/faq", methods=["GET"])
def discord_support_faq():
    q = (request.args.get("q") or request.args.get("query") or "").strip()
    from backend.services.discord_m8_streams import support_faq_answer
    return jsonify(support_faq_answer(q)), 200


@discord_bp.route("/api/discord/link", methods=["POST"])
def discord_link():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "").strip()
    discord_id = (body.get("discord_id") or body.get("discord_user_id") or "").strip()
    from backend.services.discord_link_service import link_user
    result = link_user(user_id, discord_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@discord_bp.route("/api/discord/link/status", methods=["GET"])
def discord_link_status():
    user_id = (request.args.get("user_id") or "").strip()
    from backend.services.discord_link_service import link_status
    result = link_status(user_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@discord_bp.route("/api/discord/link/unlink", methods=["POST"])
def discord_link_unlink():
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or request.args.get("user_id") or "").strip()
    from backend.services.discord_link_service import unlink_user
    result = unlink_user(user_id)
    return jsonify(result), 200 if result.get("success") else 400


@discord_bp.route("/api/discord/game/fanout", methods=["POST"])
def discord_game_fanout():
    """Gate S cron — game channel activity_events → Discord #game."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.game_discord_fanout import run_fanout
    result = run_fanout(dry_run=bool(body.get("dry_run")))
    return jsonify(result), 200


@discord_bp.route("/api/discord/shop/promo/create", methods=["POST"])
def discord_shop_promo_create():
    """M8 #52 — shop-wide Discord promo code."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.shop_discord_promo_service import create_promo
    promo = create_promo(
        reward_coins=int(body.get("reward_coins") or 75),
        reward_mn2=float(body.get("reward_mn2") or 0),
        max_redemptions=int(body.get("max_redemptions") or 200),
        ttl_hours=int(body.get("ttl_hours") or 72),
    )
    from backend.services.game_discord_fanout import run_fanout
    run_fanout()
    return jsonify(promo), 200


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
