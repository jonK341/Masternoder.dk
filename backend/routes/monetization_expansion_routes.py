"""
Monetization expansion routes — top-10 earning rails (#2–#10).
"""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

monetization_expansion_bp = Blueprint("monetization_expansion", __name__)


def _resolve_user_id():
    from backend.services.account_resolution_service import resolve_user_id

    return resolve_user_id()


def _ops_key_ok() -> bool:
    secret = (os.environ.get("COGS_ADMIN_REPORT_KEY") or os.environ.get("B2B_LEDGER_SECRET") or "").strip()
    if not secret:
        return False
    got = (request.headers.get("X-Cogs-Admin-Key") or request.headers.get("X-B2B-Ledger-Key") or request.args.get("key") or "").strip()
    return got == secret


# --- #10 Promo validate ---
@monetization_expansion_bp.route("/api/shop/promo/validate", methods=["GET", "POST"])
def shop_promo_validate():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or request.args.get("code") or "").strip()
    user_id = data.get("user_id") or request.args.get("user_id") or _resolve_user_id()
    try:
        amount = float(data.get("amount_usd") or request.args.get("amount_usd") or 0)
    except (TypeError, ValueError):
        amount = 0.0
    from backend.services.shop_checkout_promo_service import validate_checkout_promo

    out = validate_checkout_promo(code, user_id, amount_usd=amount)
    return jsonify(out), 200 if out.get("success") else 400


# --- #2 SCR self-serve ---
@monetization_expansion_bp.route("/api/monetization/scr/skus", methods=["GET"])
def scr_checkout_skus():
    from backend.services.scr_checkout_service import list_scr_checkout_skus

    return jsonify(list_scr_checkout_skus()), 200


@monetization_expansion_bp.route("/api/monetization/scr/deposit/create", methods=["POST"])
def scr_deposit_create():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or _resolve_user_id()
    sku = (data.get("studio_sku_id") or data.get("sku_id") or "").strip()
    org_label = (data.get("org_label") or "").strip() or None
    from backend.services.scr_checkout_service import create_scr_deposit_order

    out = create_scr_deposit_order(user_id, sku, org_label=org_label)
    return jsonify(out), 200 if out.get("success") else 400


# --- #5 Priority ---
@monetization_expansion_bp.route("/api/monetization/queue-priority", methods=["GET"])
def queue_priority_status():
    user_id = request.args.get("user_id") or _resolve_user_id()
    from backend.services.monetization_priority_service import priority_status

    return jsonify(priority_status(user_id)), 200


# --- #6 Premium render ---
@monetization_expansion_bp.route("/api/monetization/premium-render/quote", methods=["POST"])
def premium_render_quote():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or _resolve_user_id()
    config = data.get("config") if isinstance(data.get("config"), dict) else data
    from backend.services.generator_premium_checkout_service import quote_premium_render

    return jsonify(quote_premium_render(user_id, config)), 200


@monetization_expansion_bp.route("/api/monetization/premium-render/create-order", methods=["POST"])
def premium_render_create_order():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or _resolve_user_id()
    config = data.get("config") if isinstance(data.get("config"), dict) else data
    from backend.services.generator_premium_checkout_service import create_premium_order

    out = create_premium_order(user_id, config)
    return jsonify(out), 200 if out.get("success") else 400


# --- #7 Battle pass ---
@monetization_expansion_bp.route("/api/shop/battle-pass", methods=["GET"])
def battle_pass_status():
    user_id = request.args.get("user_id") or _resolve_user_id()
    from backend.services.battle_pass_service import get_battle_pass_status

    out = get_battle_pass_status(user_id)
    return jsonify(out), 200 if out.get("success") else 404


@monetization_expansion_bp.route("/api/shop/battle-pass/purchase", methods=["POST"])
def battle_pass_purchase():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or _resolve_user_id()
    from backend.services.battle_pass_service import purchase_battle_pass_premium

    out = purchase_battle_pass_premium(user_id, source=data.get("source") or "shop")
    return jsonify(out), 200 if out.get("success") else 400


# --- #3 API keys (admin) ---
@monetization_expansion_bp.route("/api/monetization/generator-api-keys", methods=["POST"])
def generator_api_key_create():
    if not _ops_key_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    from backend.services.generator_api_key_service import create_api_key

    out = create_api_key(
        org_label=(data.get("org_label") or "").strip(),
        user_id=(data.get("user_id") or "").strip(),
        label=data.get("label"),
    )
    return jsonify(out), 200 if out.get("success") else 400


@monetization_expansion_bp.route("/api/monetization/generator-api-keys", methods=["GET"])
def generator_api_key_list():
    if not _ops_key_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    org = (request.args.get("org_label") or "").strip()
    from backend.services.generator_api_key_service import list_keys_for_org

    return jsonify(list_keys_for_org(org)), 200


# --- #4 Camgirls PayPal ---
@monetization_expansion_bp.route("/api/camgirls/paypal/quote", methods=["GET"])
def camgirls_paypal_quote():
    action = (request.args.get("action") or "unlock").strip()
    performer_id = (request.args.get("performer_id") or "").strip()
    gift_id = request.args.get("gift_id")
    try:
        amount_mn2 = float(request.args.get("amount_mn2")) if request.args.get("amount_mn2") else None
    except (TypeError, ValueError):
        amount_mn2 = None
    from backend.services.camgirls_paypal_service import quote_action

    out = quote_action(action, performer_id, amount_mn2=amount_mn2, gift_id=gift_id)
    return jsonify(out), 200 if out.get("success") else 400


@monetization_expansion_bp.route("/api/camgirls/paypal/create-order", methods=["POST"])
def camgirls_paypal_create():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or _resolve_user_id()
    from backend.services.camgirls_paypal_service import create_paypal_order

    out = create_paypal_order(
        user_id,
        (data.get("action") or "unlock").strip(),
        (data.get("performer_id") or "").strip(),
        amount_mn2=data.get("amount_mn2"),
        gift_id=data.get("gift_id"),
    )
    return jsonify(out), 200 if out.get("success") else 400


@monetization_expansion_bp.route("/api/camgirls/paypal/capture", methods=["POST"])
def camgirls_paypal_capture():
    data = request.get_json(silent=True) or {}
    order_id = (data.get("order_id") or request.args.get("order_id") or "").strip()
    user_id = data.get("user_id") or _resolve_user_id()
    from backend.services.camgirls_paypal_service import fulfill_capture

    out = fulfill_capture(order_id, user_id=user_id)
    return jsonify(out), 200 if out.get("success") else 400


# --- #8 Masternode hosting monthly info ---
@monetization_expansion_bp.route("/api/mn2/masternode/hosting/subscription", methods=["GET"])
def masternode_hosting_subscription_info():
    import json

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "mn2_masternode_config.json",
    )
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    sub = cfg.get("paypal_monthly") if isinstance(cfg.get("paypal_monthly"), dict) else {}
    return jsonify({
        "success": True,
        "enabled": bool(sub.get("enabled")),
        "price_usd_monthly": sub.get("price_usd_monthly"),
        "label": sub.get("label"),
        "plan_note": sub.get("plan_note"),
        "create_subscription": "POST /api/monetization/subscription/create with plan_id from monetization_config",
    }), 200


# --- Tier B bundles ---
@monetization_expansion_bp.route("/api/shop/tier-b/onramp-hosting", methods=["GET"])
def tier_b_onramp_hosting():
    user_id = request.args.get("user_id") or _resolve_user_id()
    from backend.services.tier_b_monetization_service import get_onramp_hosting_offer

    return jsonify(get_onramp_hosting_offer(user_id)), 200


@monetization_expansion_bp.route("/api/shop/tier-b/auction-fee", methods=["GET"])
def tier_b_auction_fee():
    from backend.services.tier_b_monetization_service import get_auction_fee_info

    return jsonify(get_auction_fee_info()), 200


@monetization_expansion_bp.route("/api/mn2/copy-trading/premium", methods=["GET"])
def copy_trading_premium_status():
    user_id = request.args.get("user_id") or _resolve_user_id()
    from backend.services.tier_b_monetization_service import get_copy_trading_premium_status

    return jsonify(get_copy_trading_premium_status(user_id)), 200


@monetization_expansion_bp.route("/api/mn2/copy-trading/premium/purchase", methods=["POST"])
def copy_trading_premium_purchase():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or _resolve_user_id()
    from backend.services.tier_b_monetization_service import purchase_copy_trading_premium

    out = purchase_copy_trading_premium(user_id, source=data.get("source") or "shop_coins")
    return jsonify(out), 200 if out.get("success") else 400


@monetization_expansion_bp.route("/api/shop/battle-pass/quests", methods=["GET"])
def battle_pass_quests():
    user_id = request.args.get("user_id") or _resolve_user_id()
    from backend.services.battle_pass_service import get_battle_pass_status

    return jsonify(get_battle_pass_status(user_id)), 200


# --- Tier D3 mobile IAP ---
@monetization_expansion_bp.route("/api/mobile/iap/catalog", methods=["GET"])
def mobile_iap_catalog():
    from backend.services.mobile_iap_service import public_catalog
    return jsonify(public_catalog()), 200


@monetization_expansion_bp.route("/api/mobile/iap/fulfill", methods=["POST"])
def mobile_iap_fulfill():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or _resolve_user_id()
    from backend.services.mobile_iap_service import fulfill_purchase

    out = fulfill_purchase(
        user_id,
        platform=(data.get("platform") or "").strip(),
        store_product_id=(data.get("store_product_id") or data.get("product_id") or "").strip(),
        receipt_data=(data.get("receipt_data") or data.get("receipt") or "").strip(),
        transaction_id=(data.get("transaction_id") or "").strip() or None,
    )
    code = 200 if out.get("success") else 400
    if out.get("error") == "auth_required":
        code = 401
    return jsonify(out), code
