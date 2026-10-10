"""NFT catalog, primary sale, and resale book."""
from __future__ import annotations

import os
import urllib.parse

from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services.account_security_service import check_purchase_action
from backend.services import nft_exchange_service as nft

nft_bp = Blueprint("nft", __name__)


def _uid(from_body: bool = False) -> str:
    if from_body:
        data = request.get_json(silent=True) or {}
        if data.get("user_id"):
            return str(data["user_id"]).strip()
    return resolve_user_id(from_body=from_body, from_query=True)


def _base_url() -> str:
    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    if base.endswith("/vidgenerator"):
        base = base.rsplit("/vidgenerator", 1)[0]
    return base or request.url_root.rstrip("/")


@nft_bp.route("/api/nft/catalog", methods=["GET"])
def nft_catalog():
    return jsonify(nft.catalog())


@nft_bp.route("/api/nft/listings", methods=["GET"])
def nft_listings():
    limit = int(request.args.get("limit") or 50)
    return jsonify(nft.open_listings(limit=limit))


@nft_bp.route("/api/nft/deals", methods=["GET"])
def nft_deals():
    limit = int(request.args.get("limit") or 20)
    return jsonify(nft.deals(limit=limit))


@nft_bp.route("/api/nft/holdings", methods=["GET"])
def nft_holdings():
    return jsonify(nft.holdings(_uid()))


@nft_bp.route("/api/nft/buy-coins", methods=["POST"])
def nft_buy_coins():
    data = request.get_json(silent=True) or {}
    result = nft.buy_with_coins(_uid(from_body=True), data.get("sku"))
    return jsonify(result), 200 if result.get("success") else 400


@nft_bp.route("/api/nft/buy-paypal", methods=["POST"])
def nft_buy_paypal():
    """Start a PayPal checkout at the catalog USD price. Capture mints the serial."""
    data = request.get_json(silent=True) or {}
    user_id = _uid(from_body=True)
    sku = str(data.get("sku") or "").strip()
    sku_row = nft.paypal_item_map().get(sku)
    if not sku_row:
        return jsonify({"success": False, "error": "unknown_sku"}), 400
    if not user_id or user_id.lower() == "default_user":
        return jsonify({
            "success": False,
            "error": "Create an account first",
            "code": "ACCOUNT_REQUIRED",
        }), 400

    amount = float(sku_row["price_usd"])
    token = (data.get("verification_token") or data.get("security_token") or "").strip() or None
    sec_err = check_purchase_action(user_id, verification_token=token, price_usd=amount)
    if sec_err:
        return jsonify({
            "success": False,
            "error": sec_err,
            "code": "PASSWORD_VERIFICATION_REQUIRED",
            "requires_verification": True,
        }), 403

    base = _base_url()
    item_name = sku_row.get("name") or sku
    return_url = (
        f"{base}/market?paypal=success"
        f"&item_id={urllib.parse.quote(sku)}"
        f"&user_id={urllib.parse.quote(user_id)}"
    )
    cancel_url = f"{base}/market?paypal=cancel"
    try:
        from backend.services.paypal_service import create_order, remember_shop_order

        result = create_order(
            amount=amount,
            currency="USD",
            item_name=item_name,
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": sku, "user_id": user_id, "kind": "nft"},
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    if not result.get("success"):
        return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500
    try:
        remember_shop_order(result.get("order_id"), {
            "status": "pending",
            "item_id": sku,
            "item_name": item_name,
            "user_id": user_id,
            "amount": amount,
            "currency": "USD",
        })
    except Exception:
        pass
    return jsonify({
        "success": True,
        "order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "amount": amount,
        "item_id": sku,
        "item_name": item_name,
    })


@nft_bp.route("/api/nft/list", methods=["POST"])
def nft_list():
    data = request.get_json(silent=True) or {}
    result = nft.list_for_sale(_uid(from_body=True), data.get("edition_id"), data.get("price_coins"))
    return jsonify(result), 200 if result.get("success") else 400


@nft_bp.route("/api/nft/buy", methods=["POST"])
def nft_buy_listing():
    data = request.get_json(silent=True) or {}
    result = nft.buy_listing(_uid(from_body=True), data.get("listing_id"))
    return jsonify(result), 200 if result.get("success") else 400


@nft_bp.route("/api/nft/cancel", methods=["POST"])
def nft_cancel():
    data = request.get_json(silent=True) or {}
    result = nft.cancel_listing(_uid(from_body=True), data.get("listing_id"))
    return jsonify(result), 200 if result.get("success") else 400


@nft_bp.route("/api/nft/wallet", methods=["GET"])
def nft_wallet():
    return jsonify(nft.wallet_summary(_uid()))


@nft_bp.route("/api/nft/avatar-presets", methods=["GET"])
def nft_avatar_presets():
    return jsonify(nft.avatar_presets_for_user(_uid()))


@nft_bp.route("/api/nft/emblems", methods=["GET"])
def nft_emblems():
    return jsonify(nft.emblems_for_user(_uid()))


@nft_bp.route("/api/nft/equip-avatar", methods=["POST"])
def nft_equip_avatar():
    data = request.get_json(silent=True) or {}
    result = nft.equip_avatar(_uid(from_body=True), data.get("edition_id"))
    return jsonify(result), 200 if result.get("success") else 400
