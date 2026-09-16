"""Trader staking agents — profile panel status API."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id

agent_trader_staking_bp = Blueprint("agent_trader_staking", __name__)


@agent_trader_staking_bp.route("/api/agents/trader-staking/status", methods=["GET"])
def trader_staking_status():
    user_id = resolve_user_id(from_body=False, from_query=True)
    from backend.services.agent_trader_staking_service import list_trader_agents_status

    return jsonify(list_trader_agents_status(follower_user_id=user_id)), 200
