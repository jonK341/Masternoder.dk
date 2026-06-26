"""Agent API for autonomous casino play."""
import os
from flask import Blueprint, jsonify, request

import backend.services.casino_agents_service as agents

agent_casino_bp = Blueprint("agent_casino", __name__)


def _secret() -> str:
    return (os.environ.get("AGENT_CASINO_SECRET") or "").strip()


def _authorized() -> bool:
    secret = _secret()
    if not secret:
        return False
    got = (request.headers.get("X-Agent-Casino-Key") or request.args.get("agent_casino_key") or "").strip()
    return got == secret


@agent_casino_bp.route("/api/agent/casino/models", methods=["GET"])
def casino_agent_models():
    return jsonify(agents.list_models()), 200


@agent_casino_bp.route("/api/agent/casino/agents", methods=["GET"])
def casino_agent_agents():
    return jsonify(agents.list_agents()), 200


@agent_casino_bp.route("/api/agent/casino/run-all", methods=["POST"])
def casino_agent_run_all():
    if not _authorized():
        return jsonify({
            "success": False,
            "error": "Unauthorized",
            "hint": "Set AGENT_CASINO_SECRET and send header X-Agent-Casino-Key.",
        }), 403
    data = request.get_json(silent=True) or {}
    dry_run = bool(data.get("dry_run"))
    return jsonify(agents.run_all(dry_run=dry_run)), 200


@agent_casino_bp.route("/api/agent/casino/run/<agent_id>", methods=["POST"])
def casino_agent_run_one(agent_id):
    if not _authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    return jsonify(agents.run_agent(agent_id, dry_run=bool(data.get("dry_run")))), 200


@agent_casino_bp.route("/api/agent/casino/mobile/config", methods=["GET"])
def casino_agent_mobile_config():
    from backend.services import casino_social_service
    return jsonify(casino_social_service.get_mobile_config()), 200


@agent_casino_bp.route("/api/agent/casino/social/links", methods=["GET"])
def casino_agent_social_links():
    from backend.services import casino_social_service
    return jsonify(casino_social_service.get_social_links()), 200


@agent_casino_bp.route("/api/agent/casino/share/big-win", methods=["POST"])
def casino_agent_share_big_win():
    from backend.services import casino_social_service
    data = request.get_json(silent=True) or {}
    user_id = (data.get("user_id") or "").strip() or "default_user"
    mult = data.get("multiplier")
    result = casino_social_service.build_big_win_share(
        user_id,
        game=(data.get("game") or "").strip() or None,
        net=data.get("net"),
        currency=(data.get("currency") or "").strip() or None,
        multiplier=float(mult) if mult is not None else None,
        bet_id=(data.get("bet_id") or "").strip() or None,
    )
    return jsonify(result), 200 if result.get("success") else 400


@agent_casino_bp.route("/api/agent/casino/social/referral", methods=["GET"])
def casino_agent_social_referral():
    from backend.services import casino_social_service
    user_id = (request.args.get("user_id") or "").strip() or "default_user"
    return jsonify(casino_social_service.get_referral_invite(user_id)), 200


@agent_casino_bp.route("/api/agent/casino/social/follow", methods=["GET", "POST"])
def casino_agent_social_follow():
    from backend.services import casino_social_service
    user_id = (request.args.get("user_id") or (request.get_json(silent=True) or {}).get("user_id") or "").strip() or "default_user"
    if request.method == "GET":
        return jsonify(casino_social_service.get_top_players_to_follow(
            user_id,
            period=request.args.get("period", "week"),
            limit=request.args.get("limit", 5, type=int),
            currency=(request.args.get("currency") or "coins"),
        )), 200
    data = request.get_json(silent=True) or {}
    target = (data.get("target_user_id") or "").strip()
    return jsonify(casino_social_service.follow_player(user_id, target)), 200


@agent_casino_bp.route("/api/agent/casino/social/crew-challenge", methods=["GET"])
def casino_agent_social_crew_challenge():
    from backend.services import casino_social_service
    user_id = (request.args.get("user_id") or "").strip() or "default_user"
    return jsonify(casino_social_service.get_crew_casino_challenge_hook(
        user_id, currency=(request.args.get("currency") or "coins"),
    )), 200


@agent_casino_bp.route("/api/agent/casino/discord/notify", methods=["POST"])
def casino_agent_discord_notify():
    if not _authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    from backend.services import casino_discord_fanout
    data = request.get_json(silent=True) or {}
    return jsonify(casino_discord_fanout.run_fanout(dry_run=bool(data.get("dry_run")))), 200


@agent_casino_bp.route("/api/agent/casino/global/leaderboard", methods=["GET"])
def casino_agent_global_leaderboard():
    from backend.services import casino_global_controller
    period = request.args.get("period", "today")
    limit = request.args.get("limit", 25)
    user_id = (request.args.get("user_id") or "").strip() or None
    currency = (request.args.get("currency") or "coins").strip().lower()
    return jsonify(casino_global_controller.get_global_leaderboard(
        period=period, limit=limit, user_id=user_id, currency=currency,
    )), 200


@agent_casino_bp.route("/api/agent/casino/global/stats", methods=["GET"])
def casino_agent_global_stats():
    from backend.services import casino_global_controller
    return jsonify(casino_global_controller.get_global_stats()), 200


@agent_casino_bp.route("/api/agent/casino/revenue/daily", methods=["GET"])
def casino_agent_revenue_daily():
    from backend.services import casino_revenue_report
    days = request.args.get("days", 7)
    return jsonify(casino_revenue_report.daily_reports(days=days)), 200


@agent_casino_bp.route("/api/agent/casino/revenue/report/today", methods=["GET"])
def casino_agent_revenue_today():
    from backend.services import casino_revenue_report
    return jsonify(casino_revenue_report.today_summary()), 200
