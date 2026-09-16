"""
Wallet v2 API — fast summary and future BFF endpoints for /wallets SPA.
"""
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services.wallet_v2_service import build_discord_status, build_summary

wallet_v2_bp = Blueprint("wallet_v2", __name__)


@wallet_v2_bp.route("/api/wallet/v2/summary", methods=["GET"])
def wallet_v2_summary():
    """
    Fast wallet overview: balance, trophy counts, flags, network snapshot.
    Does NOT call deposit-address RPC — deposit fetch is Receive-tab only.
    """
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    sections = request.args.get("sections")
    payload = build_summary(user_id, sections_raw=sections)
    return jsonify(payload), 200


@wallet_v2_bp.route("/api/wallet/v2/discord/status", methods=["GET"])
def wallet_v2_discord_status():
    """Discord link state for wallet Settings panel."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    return jsonify(build_discord_status(user_id)), 200
