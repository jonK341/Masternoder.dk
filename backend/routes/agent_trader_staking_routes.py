"""Trader agent staking pool routes (ops join + profile dashboard)."""
from __future__ import annotations

import os
from flask import Blueprint, jsonify, request

agent_trader_staking_bp = Blueprint("agent_trader_staking", __name__)


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
    return request.headers.get("X-Ops-Secret") == secret


def _resolve_user_id() -> str:
    """Fast path for dashboard polling — avoid user_identification on default_user."""
    uid = (request.args.get("user_id") or request.headers.get("X-User-Id") or "").strip()
    if uid:
        return uid
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(
            from_body=False,
            from_query=False,
            use_session=True,
            use_identification=False,
        )
    except Exception:
        return "default_user"


@agent_trader_staking_bp.route("/api/agents/trader-staking/status", methods=["GET"])
def trader_staking_status():
    from backend.services.agent_trader_staking_service import list_trader_agents_status
    uid = _resolve_user_id()
    try:
        result = list_trader_agents_status(follower_user_id=uid)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@agent_trader_staking_bp.route("/api/agents/trader-staking/join-pool", methods=["POST"])
def trader_staking_join_pool():
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run"))
    from backend.services.agent_trader_staking_service import join_trader_agents_to_pool
    result = join_trader_agents_to_pool(dry_run=dry_run)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@agent_trader_staking_bp.route("/api/agents/trader-staking/run-market", methods=["POST"])
def trader_staking_run_market():
    """Ops: run one market tick for all trader agents (sell + cross-buy)."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    from backend.services.agent_trader_service import run_all_traders
    result = run_all_traders()
    return jsonify(result), 200 if result.get("success") else 400
