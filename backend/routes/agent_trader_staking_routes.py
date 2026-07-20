"""Trader agent staking status + copy-trading discovery (Stage 2)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

agent_trader_staking_bp = Blueprint("agent_trader_staking", __name__)


@agent_trader_staking_bp.route("/api/agents/trader-staking/status", methods=["GET"])
def trader_staking_status():
    from backend.services.agent_trader_staking_service import list_trader_agents_status

    user_id = (request.args.get("user_id") or "").strip() or None
    return jsonify(list_trader_agents_status(follower_user_id=user_id)), 200


@agent_trader_staking_bp.route("/api/mn2/copy-trading/follow", methods=["POST"])
def copy_trading_follow():
    data = request.get_json(silent=True) or {}
    user_id = (data.get("user_id") or request.args.get("user_id") or "").strip()
    leader = (data.get("leader_agent_id") or "").strip()
    if not user_id or not leader:
        return jsonify({"success": False, "error": "user_id and leader_agent_id required"}), 400
    from backend.services.mn2_copy_trading import upsert_follower

    result = upsert_follower(
        user_id,
        leader,
        scale=float(data.get("scale") or 0.25),
        max_mn2_per_step=float(data.get("max_mn2_per_step") or 25),
        enabled=bool(data.get("enabled", True)),
    )
    return jsonify(result), 200 if result.get("success") else 400


@agent_trader_staking_bp.route("/api/mn2/copy-trading/unfollow", methods=["POST"])
def copy_trading_unfollow():
    data = request.get_json(silent=True) or {}
    user_id = (data.get("user_id") or request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    from backend.services.mn2_copy_trading import remove_follower

    result = remove_follower(user_id)
    return jsonify(result), 200 if result.get("success") else 400
