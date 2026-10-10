"""Index routes the debugger page prefixes, plus the admin unlock handshake.

The page builds URLs from /api/debug, /api/debugger/*, /api/debugging, and
/api/ai-agents. Those prefixes 404'd on their own. Joke health-quiz paths are
real admin-only responses so a scanner does not treat them as missing.
"""
from flask import Blueprint, jsonify, request

from backend.services.admin_gate import grant_admin_session, protect_blueprint

debugger_shell_bp = Blueprint("debugger_shell", __name__)


def _index(name, children):
    return jsonify({
        "success": True,
        "service": name,
        "endpoints": children,
    }), 200


@debugger_shell_bp.route("/api/debugger/unlock", methods=["POST"])
def debugger_unlock():
    """Store an admin session when the supplied key matches a configured secret."""
    from backend.services.admin_gate import configured_admin_secrets

    if not configured_admin_secrets():
        return jsonify({
            "success": False,
            "error": "admin_auth_not_configured",
            "hint": "Set COGS_ADMIN_REPORT_KEY, EXCHANGE_ADMIN_KEY, or DEBUGGER_ADMIN_KEY",
        }), 503
    body = request.get_json(silent=True) or {}
    secret = str(body.get("admin_key") or body.get("key") or request.headers.get("X-Admin-Key") or "").strip()
    if not grant_admin_session(secret):
        return jsonify({"success": False, "error": "admin_required", "code": "admin_required"}), 401
    return jsonify({"success": True, "admin": True}), 200


@debugger_shell_bp.route("/api/debug", methods=["GET"])
def debug_index():
    return _index("debug", [
        "/api/debug/all-systems",
        "/api/debug/all-routes",
        "/api/debug/report",
        "/api/debug/check-duplicates",
    ])


@debugger_shell_bp.route("/api/debugging", methods=["GET"])
def debugging_index():
    return _index("debugging", [
        "/api/debugging/master/status",
        "/api/debugging/stats",
        "/api/debugging/profiles",
    ])


@debugger_shell_bp.route("/api/debugger/agent", methods=["GET"])
def debugger_agent_index():
    return _index("debugger-agent", [
        "/api/debugger/agent/fix-all",
        "/api/debugger/agent/analytics",
        "/api/debugger/agent/handling",
    ])


@debugger_shell_bp.route("/api/debugger/profile", methods=["GET"])
def debugger_profile_index():
    return _index("debugger-profile", [
        "/api/debugger/profile/points",
        "/api/debugger/profile/stats",
        "/api/debugger/profile/agent-points",
    ])


@debugger_shell_bp.route("/api/debugger/tasks", methods=["GET"])
def debugger_tasks_index():
    return _index("debugger-tasks", [
        "/api/debugger/tasks/list",
        "/api/debugger/tasks/stats",
    ])


@debugger_shell_bp.route("/api/ai-agents", methods=["GET"])
def ai_agents_index():
    return _index("ai-agents", ["/api/ai-agents/create"])


@debugger_shell_bp.route("/api/horoscope", methods=["GET"])
def horoscope():
    return jsonify({
        "success": True,
        "sign": "debugger",
        "message": "The stack trace is the only horoscope that pays out.",
    }), 200


@debugger_shell_bp.route("/api/teleport", methods=["GET"])
def teleport():
    return jsonify({
        "success": True,
        "destination": "/debugger",
        "message": "No teleport. Use the debugger tabs.",
    }), 200


@debugger_shell_bp.route("/api/make/coffee", methods=["GET"])
def make_coffee():
    return jsonify({
        "success": False,
        "error": "i_am_a_teapot",
        "message": "This server brews stack traces, not coffee.",
    }), 418


protect_blueprint(debugger_shell_bp, skip_paths={"/api/debugger/unlock"})
