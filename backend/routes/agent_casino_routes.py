"""
Agent automation layer for casino leaderboard play.

Gives headless / cron agents full parity with the casino play APIs: discover
specialized casino AI models, read leaderboard status, and execute one play step
per persona per tick.

Requires AGENT_CASINO_SECRET (falls back to AGENT_CRON_SECRET).
Send as header X-Agent-Casino-Key (or ?agent_casino_key=).
"""
import os
from flask import Blueprint, jsonify, request

import backend.services.casino_agents_service as casino_agents

agent_casino_bp = Blueprint("agent_casino", __name__)


def _secret() -> str:
    return (
        os.environ.get("AGENT_CASINO_SECRET")
        or os.environ.get("AGENT_CRON_SECRET")
        or os.environ.get("AGENT_MN2_SHOP_SECRET")
        or ""
    ).strip()


def _authorized() -> bool:
    secret = _secret()
    if not secret:
        return False
    got = (
        request.headers.get("X-Agent-Casino-Key")
        or request.args.get("agent_casino_key")
        or ""
    ).strip()
    return got == secret


_CAPABILITIES = [
    {"action": "list_models", "method": "GET", "params": [],
     "description": "List specialized casino AI model archetypes (Kelly, Martingale, Slot Hunter, …)."},
    {"action": "list_agents", "method": "GET", "params": [],
     "description": "List casino personas (agent_id → user_id + policy)."},
    {"action": "upsert_agent", "method": "POST", "params": ["agent_id", "user_id", "policy?"],
     "description": "Create/update a casino persona."},
    {"action": "run_agent", "method": "POST", "params": ["agent_id", "dry_run?"],
     "description": "Execute one play step for a persona (one bet toward leaderboard)."},
    {"action": "run_all", "method": "POST", "params": ["dry_run?"],
     "description": "Execute one play step for every enabled casino persona."},
    {"action": "leaderboard", "method": "GET", "params": ["period?", "limit?"],
     "description": "Leaderboard snapshot with agent rows highlighted."},
]


@agent_casino_bp.route("/api/agent/casino/capabilities", methods=["GET"])
def casino_agent_capabilities():
    return jsonify({"success": True, "capabilities": _CAPABILITIES}), 200


@agent_casino_bp.route("/api/agent/casino/models", methods=["GET"])
def casino_agent_models():
    return jsonify(casino_agents.list_models()), 200


@agent_casino_bp.route("/api/agent/casino/agents", methods=["GET"])
def casino_agent_list():
    return jsonify(casino_agents.list_agents()), 200


@agent_casino_bp.route("/api/agent/casino/agents", methods=["POST"])
def casino_agent_upsert():
    if not _authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    return jsonify(casino_agents.upsert_agent(
        data.get("agent_id") or "",
        data.get("user_id") or "",
        policy=data.get("policy"),
    )), 200


@agent_casino_bp.route("/api/agent/casino/run", methods=["POST"])
def casino_agent_run():
    if not _authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    agent_id = (data.get("agent_id") or request.args.get("agent_id") or "").strip()
    if not agent_id:
        return jsonify({"success": False, "error": "agent_id required"}), 400
    dry = bool(data.get("dry_run") or request.args.get("dry_run") in ("1", "true"))
    result = casino_agents.run_agent(agent_id, dry_run=dry)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@agent_casino_bp.route("/api/agent/casino/run-all", methods=["POST"])
def casino_agent_run_all():
    if not _authorized():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    dry = bool(data.get("dry_run") or request.args.get("dry_run") in ("1", "true"))
    return jsonify(casino_agents.run_all(dry_run=dry)), 200


@agent_casino_bp.route("/api/agent/casino/leaderboard", methods=["GET"])
def casino_agent_leaderboard():
    period = request.args.get("period") or "week"
    limit = request.args.get("limit", 20, type=int)
    return jsonify(casino_agents.leaderboard_snapshot(period=period, limit=limit)), 200


@agent_casino_bp.route("/api/agent/casino/plan", methods=["GET", "POST"])
def casino_agent_plan():
    """Preview LLM/heuristic bet plan without executing."""
    agent_id = (request.args.get("agent_id") or "").strip()
    if not agent_id and request.method == "POST":
        data = request.get_json(silent=True) or {}
        agent_id = (data.get("agent_id") or "").strip()
    if not agent_id:
        return jsonify({"success": False, "error": "agent_id required"}), 400
    return jsonify(casino_agents.plan_agent(agent_id)), 200


@agent_casino_bp.route("/api/agent/casino/brain", methods=["GET"])
def casino_agent_brain():
    """Recent LLM reasoning log for one or all casino agents."""
    agent_id = (request.args.get("agent_id") or "").strip() or None
    limit = request.args.get("limit", 10, type=int)
    return jsonify(casino_agents.agent_brain(agent_id, limit=limit)), 200


@agent_casino_bp.route("/api/agent/casino/ops/run-all", methods=["POST"])
def casino_agent_ops_run_all():
    """Ops cron entry (MN2_OPS_SECRET / DISCORD_OPS_SECRET pattern)."""
    secret = (
        os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("ADMIN_OPS_SECRET")
        or ""
    ).strip()
    if secret:
        got = request.headers.get("X-Ops-Secret") or request.args.get("ops_secret") or ""
        if got != secret:
            return jsonify({"success": False, "error": "unauthorized"}), 403
    elif request.environ.get("REMOTE_ADDR") not in ("127.0.0.1", "::1"):
        return jsonify({"success": False, "error": "unauthorized"}), 403
    return jsonify(casino_agents.run_all(dry_run=False)), 200
