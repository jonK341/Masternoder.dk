"""
Wallet v2 API — fast summary and future BFF endpoints for /wallets SPA.
"""
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services.wallet_upgrades_service import (
    build_masternode_map,
    get_progress,
    list_upgrades,
    unlock_upgrade,
)
from backend.services.wallet_micro_earn_service import get_status as micro_earn_status
from backend.services.wallet_micro_earn_service import record_click as micro_earn_click
from backend.services.camgirls_ai_features_service import (
    get_feature_detail as camgirls_get_ai_feature,
    list_features as camgirls_list_ai_features,
    trigger_feature as camgirls_trigger_ai_feature,
)
from backend.services.camgirls_wallet_service import (
    get_progress as camgirls_get_progress,
    get_wallet_detail as camgirls_get_wallet_detail,
    list_all_wallets as camgirls_list_all_wallets,
    list_performers,
    list_upgrades as camgirls_list_upgrades,
    tip_camgirl,
    unlock_upgrade as camgirls_unlock_upgrade,
)
from backend.services.network_chat_service import (
    get_status as network_chat_status,
    heartbeat as network_chat_heartbeat,
    post_message as network_chat_post_message,
    post_rating as network_chat_post_rating,
)
from backend.services.wallet_integration_service import build_integration_hub
from backend.services.wallet_v2_service import (
    build_casino_snapshot,
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


@wallet_v2_bp.route("/api/wallet/v2/discord/fulfillment-status", methods=["GET"])
def wallet_v2_discord_fulfillment_status():
    """User's row in the Discord community fulfillment order list."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    from backend.services.discord_fulfillment_ledger_service import get_user_fulfillment_status

    return jsonify(get_user_fulfillment_status(user_id)), 200


@wallet_v2_bp.route("/api/wallet/v2/discord/register-purchase-intent", methods=["POST"])
def wallet_v2_discord_register_purchase_intent():
    """Register MN2 buy intent for Discord fulfillment ledger (source 3)."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    from backend.services.discord_fulfillment_ledger_service import register_mn2_purchase_intent

    result = register_mn2_purchase_intent(
        user_id=user_id,
        discord_id=body.get("discord_id"),
        channel=body.get("channel") or "wallet",
        pack_id=body.get("pack_id"),
        amount_usd=body.get("amount_usd"),
        note=body.get("note"),
    )
    status = 200 if result.get("success") else 400
    return jsonify(result), status


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


@wallet_v2_bp.route("/api/wallet/v2/upgrades/unlock", methods=["POST"])
def wallet_v2_upgrades_unlock():
    """Unlock one upgrade when conditions are met; persists per-user progress."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    upgrade_id = body.get("upgrade_id") or request.args.get("upgrade_id")
    result = unlock_upgrade(user_id, upgrade_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


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


@wallet_v2_bp.route("/api/wallet/v2/casino/snapshot", methods=["GET"])
def wallet_v2_casino_snapshot():
    """Casino hub snapshot — balance, VIP, featured games, Discord VIP eligibility."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    return jsonify(build_casino_snapshot(user_id)), 200


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


@wallet_v2_bp.route("/api/wallet/v2/integration/hub", methods=["GET"])
def wallet_v2_integration_hub():
    """Mega integration hub — links and snapshot counts for wallet platform tabs."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    return jsonify(build_integration_hub(user_id)), 200


@wallet_v2_bp.route("/api/wallet/v2/camgirls/catalog", methods=["GET"])
def wallet_v2_camgirls_catalog():
    """25 camgirl wallet profiles — SFW cards with MN2 balance and studio deep links."""
    return jsonify(list_performers()), 200


@wallet_v2_bp.route("/api/wallet/v2/camgirls/wallets", methods=["GET"])
def wallet_v2_camgirls_all_wallets():
    """All camgirl synthetic MN2 wallets — balances and wallet_user_ids."""
    return jsonify(camgirls_list_all_wallets()), 200


@wallet_v2_bp.route("/api/wallet/v2/camgirls/<camgirl_id>/wallet", methods=["GET"])
def wallet_v2_camgirl_wallet(camgirl_id: str):
    """Single camgirl MN2 wallet — balance, wallet_user_id, optional explorer link."""
    result = camgirls_get_wallet_detail(camgirl_id)
    status = 200 if result.get("success") else 404
    return jsonify(result), status


@wallet_v2_bp.route("/api/wallet/v2/camgirls/<camgirl_id>/tip", methods=["POST"])
def wallet_v2_camgirl_tip(camgirl_id: str):
    """Tip MN2 from logged-in user to camgirl synthetic wallet."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    amount = body.get("amount_mn2") or body.get("amount") or request.args.get("amount")
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "invalid_amount"}), 400
    result = tip_camgirl(user_id, camgirl_id, amt)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@wallet_v2_bp.route("/api/wallet/v2/camgirls/upgrades", methods=["GET"])
def wallet_v2_camgirls_upgrades_list():
    """250 camgirl section upgrades catalog — lazy-loaded."""
    category = request.args.get("category")
    return jsonify(camgirls_list_upgrades(category=category)), 200


@wallet_v2_bp.route("/api/wallet/v2/camgirls/upgrades/progress", methods=["GET"])
def wallet_v2_camgirls_upgrades_progress():
    """Per-user camgirl upgrade unlock progress."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    return jsonify(camgirls_get_progress(user_id)), 200


@wallet_v2_bp.route("/api/wallet/v2/camgirls/upgrades/unlock", methods=["POST"])
def wallet_v2_camgirls_upgrades_unlock():
    """Unlock one camgirl upgrade when conditions are met."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    upgrade_id = body.get("upgrade_id") or request.args.get("upgrade_id")
    result = camgirls_unlock_upgrade(user_id, upgrade_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@wallet_v2_bp.route("/api/wallet/v2/camgirls/ai-features", methods=["GET"])
def wallet_v2_camgirls_ai_features_list():
    """100 camgirl AI feature bundles — animation + payment + sound."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    category = request.args.get("category")
    performer_id = request.args.get("performer_id")
    return jsonify(camgirls_list_ai_features(category=category, performer_id=performer_id, user_id=user_id)), 200


@wallet_v2_bp.route("/api/wallet/v2/camgirls/ai-features/<feature_id>", methods=["GET"])
def wallet_v2_camgirls_ai_feature_detail(feature_id: str):
    """Single camgirl AI feature bundle detail."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    performer_id = request.args.get("performer_id")
    result = camgirls_get_ai_feature(feature_id, performer_id=performer_id, user_id=user_id)
    status = 200 if result.get("success") else 404
    return jsonify(result), status


@wallet_v2_bp.route("/api/wallet/v2/camgirls/ai-features/<feature_id>/trigger", methods=["POST"])
def wallet_v2_camgirls_ai_feature_trigger(feature_id: str):
    """Pay MN2 (or free if upgrade-unlocked) and return animation+sound playback payload."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    performer_id = body.get("performer_id") or request.args.get("performer_id")
    result = camgirls_trigger_ai_feature(user_id, feature_id, performer_id=performer_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@wallet_v2_bp.route("/api/wallet/v2/network-chat/status", methods=["GET"])
def wallet_v2_network_chat_status():
    """Network chat room status — online users stub, recent messages, reward caps."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    limit = request.args.get("limit", "50")
    try:
        lim = int(limit)
    except (TypeError, ValueError):
        lim = 50
    return jsonify(network_chat_status(user_id, limit=lim)), 200


@wallet_v2_bp.route("/api/wallet/v2/network-chat/message", methods=["POST"])
def wallet_v2_network_chat_message():
    """Post a network chat message (JSONL store) and earn micro MN2 when within caps."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    text = body.get("text") or body.get("message") or ""
    display_name = body.get("display_name")
    result = network_chat_post_message(user_id, text, display_name=display_name)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@wallet_v2_bp.route("/api/wallet/v2/network-chat/rating", methods=["POST"])
def wallet_v2_network_chat_rating():
    """Rate a chat message 1–5 stars and earn micro MN2 for activity."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    message_id = body.get("message_id") or request.args.get("message_id")
    stars = body.get("stars") or request.args.get("stars")
    result = network_chat_post_rating(user_id, message_id, stars)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@wallet_v2_bp.route("/api/wallet/v2/network-chat/heartbeat", methods=["POST"])
def wallet_v2_network_chat_heartbeat():
    """Presence heartbeat for online roster and micro-earn."""
    user_id = resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    body = request.get_json(silent=True) or {}
    display_name = body.get("display_name")
    return jsonify(network_chat_heartbeat(user_id, display_name=display_name)), 200
