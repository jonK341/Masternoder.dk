"""Agents control board — start/stop, fund, strategy."""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

agent_admin_bp = Blueprint("agent_admin", __name__)


def _ops_ok() -> bool:
    secret = os.environ.get("DISCORD_OPS_SECRET") or os.environ.get("ADMIN_OPS_SECRET", "")
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return request.headers.get("X-Ops-Secret") == secret


@agent_admin_bp.route("/api/agents/control/status", methods=["GET"])
def agents_control_status():
    from backend.services.agent_kill_switch import get_status
    from backend.services.agent_wallet_service import list_wallets, get_treasury, get_treasury_pool_balance
    from backend.services.agent_trader_service import list_strategies
    return jsonify({
        "success": True,
        "kill_switch": get_status(),
        "treasury": get_treasury(),
        "treasury_pool_mn2": get_treasury_pool_balance(),
        "wallets": list_wallets(),
        "strategies": list_strategies(),
    }), 200


@agent_admin_bp.route("/api/agents/control/halt", methods=["POST"])
def agents_control_halt():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.agent_kill_switch import set_switch
    result = set_switch(
        global_halt=bool(body.get("global_halt", True)),
        reason=body.get("reason") or "ops_halt",
        set_by="ops",
    )
    return jsonify(result), 200


@agent_admin_bp.route("/api/agents/control/resume", methods=["POST"])
def agents_control_resume():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_kill_switch import set_switch
    result = set_switch(global_halt=False, reason="ops_resume", set_by="ops")
    return jsonify(result), 200


@agent_admin_bp.route("/api/agents/control/fund", methods=["POST"])
def agents_control_fund():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_wallet_service import distribute_agent_funding
    return jsonify(distribute_agent_funding()), 200


@agent_admin_bp.route("/api/agents/control/trader/run", methods=["POST"])
def agents_control_trader_run():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_trader_service import run_all_traders
    return jsonify(run_all_traders()), 200
