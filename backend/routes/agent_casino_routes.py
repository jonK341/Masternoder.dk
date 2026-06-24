"""Agent casino bot API — models, agents, run-all with shared secret."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

from backend.services import casino_agents_service as svc

agent_casino_bp = Blueprint("agent_casino", __name__)


def _authorized() -> bool:
    secret = (os.environ.get("AGENT_CASINO_SECRET") or "").strip()
    if not secret:
        return False
    token = (request.headers.get("X-Agent-Casino-Key") or "").strip()
    return token == secret


@agent_casino_bp.route("/api/agent/casino/models", methods=["GET"])
def agent_casino_models():
    try:
        return jsonify(svc.list_models()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_casino_bp.route("/api/agent/casino/agents", methods=["GET"])
def agent_casino_agents():
    try:
        return jsonify(svc.list_agents()), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@agent_casino_bp.route("/api/agent/casino/run-all", methods=["POST"])
def agent_casino_run_all():
    if not _authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        data = request.get_json(silent=True) or {}
        dry_run = bool(data.get("dry_run"))
        agent_ids = data.get("agent_ids")
        if agent_ids is not None and not isinstance(agent_ids, list):
            agent_ids = None
        return jsonify(svc.run_all(dry_run=dry_run, agent_ids=agent_ids)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
