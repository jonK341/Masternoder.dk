"""Trader agent staking status + copy-trading discovery (Stage 2)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

agent_trader_staking_bp = Blueprint("agent_trader_staking", __name__)


@agent_trader_staking_bp.route("/api/agents/trader-staking/status", methods=["GET"])
def trader_staking_status():
    from backend.services.agent_trader_staking_service import list_trader_agents_status

    user_id = (request.args.get("user_id") or "").strip() or None
    return jsonify(list_trader_agents_status(follower_user_id=user_id)), 200
