"""Agents control board API — treasury, traders, kill switch (Phase 4)."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

agent_admin_bp = Blueprint("agent_admin", __name__)


def _ops_ok() -> bool:
    secret = (
        os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("ADMIN_OPS_SECRET")
        or ""
    ).strip()
    provided = (
        request.headers.get("X-Ops-Secret")
        or request.args.get("ops_secret")
        or request.args.get("token")
        or ""
    ).strip()
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return bool(provided) and provided == secret


@agent_admin_bp.route("/api/agents/control/status", methods=["GET"])
def control_status():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_admin_service import get_control_status
    return jsonify(get_control_status()), 200


@agent_admin_bp.route("/api/agents/control/fund", methods=["POST"])
def control_fund():
    """Fund traders via treasury. Default dry-run until live_distribute + sign-off."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    body = request.get_json(silent=True) or {}
    # Never force live from the board; distribute_agent_funding only goes live when
    # agent_funding.live_distribute is true AND cold-wallet sign-off allows it.
    dry_run = body.get("dry_run")
    if dry_run is not None:
        dry_run = bool(dry_run)
    from backend.services.agent_wallet_service import distribute_agent_funding
    result = distribute_agent_funding(dry_run=dry_run)
    status = 200 if result.get("success") else 403
    return jsonify(result), status


@agent_admin_bp.route("/api/agents/control/trader/run", methods=["POST"])
def control_trader_run():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_trader_service import run_all_traders
    return jsonify(run_all_traders()), 200


@agent_admin_bp.route("/api/agents/control/halt", methods=["POST"])
def control_halt():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_kill_switch import set_switch
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "ops halt").strip()
    actor = (request.headers.get("X-Ops-Actor") or "ops").strip()
    result = set_switch(global_halt=True, reason=reason, set_by=actor)
    try:
        from backend.services.admin_audit_service import log_action
        log_action("agent_global_halt", actor=actor, payload={"reason": reason})
    except Exception:
        pass
    return jsonify(result), 200


@agent_admin_bp.route("/api/agents/control/resume", methods=["POST"])
def control_resume():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_kill_switch import set_switch
    actor = (request.headers.get("X-Ops-Actor") or "ops").strip()
    result = set_switch(global_halt=False, reason="", set_by=actor)
    try:
        from backend.services.admin_audit_service import log_action
        log_action("agent_global_resume", actor=actor, payload={})
    except Exception:
        pass
    return jsonify(result), 200
