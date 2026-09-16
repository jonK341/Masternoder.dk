"""
Wallet v2 API — fast summary and future BFF endpoints for /wallets SPA.
"""
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services.wallet_upgrades_service import (
    build_masternode_map,
    get_progress,
    list_upgrades,
)
from backend.services.wallet_micro_earn_service import get_status as micro_earn_status
from backend.services.wallet_micro_earn_service import record_click as micro_earn_click
from backend.services.wallet_v2_service import (
    build_discord_status,
    build_rewards_snapshot,
    build_site_features,
    build_summary,
)

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


@wallet_v2_bp.route("/api/wallet/v2/upgrades", methods=["GET"])
def wallet_v2_upgrades_list():
    """Wallet upgrades catalog — lazy-loaded, not on summary."""
    category = request.args.get("category")
    return jsonify(list_upgrades(category=category)), 200


@wallet_v2_bp.route("/api/wallet/v2/upgrades/progress", methods=["GET"])
def wallet_v2_upgrades_progress():
    """Per-user upgrade unlock progress — lazy-loaded."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    return jsonify(get_progress(user_id)), 200


@wallet_v2_bp.route("/api/wallet/v2/network/masternodes", methods=["GET"])
def wallet_v2_network_masternodes():
    """Masternode online grid for Overview map strip — lazy-loaded."""
    limit = request.args.get("limit", "48")
    try:
        lim = int(limit)
    except (TypeError, ValueError):
        lim = 48
    return jsonify(build_masternode_map(limit=lim)), 200


@wallet_v2_bp.route("/api/wallet/v2/site-features", methods=["GET"])
def wallet_v2_site_features():
    """Site feature matrix for Site Features Hub — lazy-loaded."""
    return jsonify(build_site_features()), 200


@wallet_v2_bp.route("/api/wallet/v2/rewards/snapshot", methods=["GET"])
def wallet_v2_rewards_snapshot():
    """Unified points snapshot for wallet Rewards tab — lazy-loaded."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    return jsonify(build_rewards_snapshot(user_id)), 200


@wallet_v2_bp.route("/api/wallet/v2/earn/status", methods=["GET"])
def wallet_v2_earn_status():
    """Micro-earn progress: today's totals, caps, and per-event availability."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    return jsonify(micro_earn_status(user_id)), 200


@wallet_v2_bp.route("/api/wallet/v2/earn/click", methods=["POST"])
def wallet_v2_earn_click():
    """Record a click-to-earn event and credit micro MN2 when within caps."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    event_id = body.get("event_id") or request.args.get("event_id")
    captcha_token = body.get("captcha_token")
    result = micro_earn_click(user_id, event_id, captcha_token=captcha_token)
    status = 200 if result.get("success") else 400
    return jsonify(result), status
