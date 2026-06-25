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


@agent_casino_bp.route("/api/agent/casino/discord/notify", methods=["POST"])
def casino_agent_discord_notify():
    if not _authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    from backend.services import casino_discord_fanout
    data = request.get_json(silent=True) or {}
    return jsonify(casino_discord_fanout.run_fanout(dry_run=bool(data.get("dry_run")))), 200
