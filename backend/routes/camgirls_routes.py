"""Camgirls API routes."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

camgirls_bp = Blueprint("camgirls", __name__)


def _uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        data = request.get_json(silent=True) or {}
        return (data.get("user_id") or request.args.get("user_id") or "default_user").strip()


@camgirls_bp.route("/api/camgirls/performers", methods=["GET"])
def performers_list():
    from backend.services.camgirls_service import list_performers_catalog
    return jsonify(list_performers_catalog(user_id=_uid())), 200


@camgirls_bp.route("/api/camgirls/age-verify", methods=["POST"])
def age_verify():
    from backend.services.camgirls_service import record_age_verification
    data = request.get_json(silent=True) or {}
    year = data.get("birth_year") or request.args.get("birth_year")
    try:
        year = int(year)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "birth_year required"}), 400
    return jsonify(record_age_verification(_uid(), year)), 200


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/unlock", methods=["POST"])
def performer_unlock(performer_id: str):
    from backend.services.camgirls_service import unlock_performer
    return jsonify(unlock_performer(_uid(), performer_id)), 200


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/tip", methods=["POST"])
def performer_tip(performer_id: str):
    from backend.services.camgirls_service import tip_performer
    data = request.get_json(silent=True) or {}
    amount = float(data.get("amount") or 0)
    return jsonify(tip_performer(_uid(), performer_id, amount)), 200


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/chat", methods=["POST"])
def performer_chat(performer_id: str):
    from backend.services.camgirls_service import chat_with_performer
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    return jsonify(chat_with_performer(_uid(), performer_id, message)), 200


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/chat/history", methods=["GET"])
def performer_chat_history(performer_id: str):
    from backend.services.camgirls_service import get_chat_history
    limit = request.args.get("limit", 30, type=int)
    return jsonify(get_chat_history(_uid(), performer_id, limit=limit)), 200


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/favorite", methods=["POST"])
def performer_favorite(performer_id: str):
    from backend.services.camgirls_social_service import toggle_favorite
    return jsonify(toggle_favorite(_uid(), performer_id)), 200


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/fan-club", methods=["POST"])
def performer_fan_club(performer_id: str):
    from backend.services.camgirls_social_service import join_fan_club
    return jsonify(join_fan_club(_uid(), performer_id)), 200


@camgirls_bp.route("/api/camgirls/performers/<performer_id>/goal", methods=["GET"])
def performer_goal(performer_id: str):
    from backend.services.camgirls_social_service import get_goal_status
    return jsonify(get_goal_status(performer_id)), 200


@camgirls_bp.route("/api/camgirls/studio/catalog", methods=["GET"])
def studio_catalog_route():
    from backend.services.camgirls_studio_service import studio_catalog
    return jsonify(studio_catalog()), 200


@camgirls_bp.route("/api/camgirls/agent-tools", methods=["GET"])
def agent_tools():
    from backend.services.camgirls_agents_service import list_agent_tools
    return jsonify({"success": True, "tools": list_agent_tools()}), 200


@camgirls_bp.route("/api/camgirls/agents", methods=["GET"])
def agents_roster():
    from backend.services.camgirls_agents_service import list_agent_models
    agents = list_agent_models()
    return jsonify({"success": True, "agents": agents, "count": len(agents)}), 200


@camgirls_bp.route("/api/camgirls/agent-action", methods=["POST"])
def agent_action():
    from backend.services.camgirls_agents_service import execute_agent_action
    data = request.get_json(silent=True) or {}
    action = data.get("action") or ""
    approved = bool(data.get("approved"))
    return jsonify(execute_agent_action(action, _uid(), approved=approved, **data)), 200


@camgirls_bp.route("/api/camgirls/status", methods=["GET"])
def platform_status_route():
    from backend.services.camgirls_status_service import platform_status
    return jsonify(platform_status()), 200


@camgirls_bp.route("/api/camgirls/livekit/status", methods=["GET"])
def livekit_status_route():
    from backend.services.camgirls_livekit_service import public_status
    return jsonify({"success": True, **public_status()}), 200


@camgirls_bp.route("/api/camgirls/livekit/token", methods=["POST"])
def livekit_token_route():
    from backend.services.camgirls_livekit_service import issue_room_token
    data = request.get_json(silent=True) or {}
    performer_id = (data.get("performer_id") or request.args.get("performer_id") or "").strip()
    return jsonify(issue_room_token(_uid(), performer_id)), 200
