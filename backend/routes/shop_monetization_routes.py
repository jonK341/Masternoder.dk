"""
Shop V9.2 monetization routes.

Surfaces the revenue mechanics from shop_monetization_service:
VIP pass, mystery boxes, spin wheel, flash sales, gifting, loyalty/cashback,
and featured auction listings. Registered as its own blueprint so the large
shop_routes module stays focused on the core catalog/purchase flow.
"""
from flask import Blueprint, jsonify, request

from backend.services import shop_monetization_service as mon

shop_monetization_bp = Blueprint("shop_monetization", __name__)


def _uid():
    from backend.services.account_resolution_service import resolve_user_id

    return resolve_user_id()


def _req_uid(data):
    return (
        (data.get("user_id") if isinstance(data, dict) else None)
        or request.args.get("user_id")
        or _uid()
    )


@shop_monetization_bp.route("/api/shop/monetization/overview", methods=["GET"])
def monetization_overview():
    try:
        user_id = request.args.get("user_id") or _uid()
        return jsonify({"success": True, "user_id": user_id, "overview": mon.get_overview(user_id),
                        "version": mon.get_config().get("version") or "9.2.0"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- VIP ----------------

@shop_monetization_bp.route("/api/shop/vip/status", methods=["GET"])
def vip_status():
    try:
        user_id = request.args.get("user_id") or _uid()
        return jsonify({"success": True, "user_id": user_id, "vip": mon.get_vip_status(user_id)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_monetization_bp.route("/api/shop/vip/claim-daily", methods=["POST"])
def vip_claim_daily():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _req_uid(data)
        result = mon.claim_vip_daily(user_id)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- Mystery boxes ----------------

@shop_monetization_bp.route("/api/shop/mystery-boxes", methods=["GET"])
def mystery_boxes():
    try:
        user_id = request.args.get("user_id") or _uid()
        return jsonify({"success": True, "boxes": mon.list_mystery_boxes(user_id)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "boxes": []}), 500


@shop_monetization_bp.route("/api/shop/mystery-box/open", methods=["POST"])
def open_box():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _req_uid(data)
        box_id = data.get("box_id") or request.args.get("box_id")
        method = (data.get("payment_method") or "coins").strip().lower()
        if not box_id:
            return jsonify({"success": False, "error": "box_id is required"}), 400
        result = mon.open_mystery_box(user_id, box_id, payment_method=method)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- Spin wheel ----------------

@shop_monetization_bp.route("/api/shop/spin-wheel", methods=["GET"])
def spin_status():
    try:
        user_id = request.args.get("user_id") or _uid()
        return jsonify({"success": True, "user_id": user_id, "spin": mon.get_spin_status(user_id)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_monetization_bp.route("/api/shop/spin-wheel/spin", methods=["POST"])
def spin():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _req_uid(data)
        paid = bool(data.get("paid"))
        method = (data.get("payment_method") or "coins").strip().lower()
        result = mon.spin_wheel(user_id, paid=paid, payment_method=method)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- Flash sales ----------------

@shop_monetization_bp.route("/api/shop/flash-sales", methods=["GET"])
def flash_sales():
    try:
        return jsonify({"success": True, **mon.get_flash_sales()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "sales": []}), 500


# ---------------- Gifting ----------------

@shop_monetization_bp.route("/api/shop/gift", methods=["POST"])
def gift():
    try:
        data = request.get_json(silent=True) or {}
        sender = _req_uid(data)
        recipient = (data.get("recipient_id") or "").strip()
        coins = int(data.get("coins") or 0)
        message = (data.get("message") or "").strip()
        result = mon.gift_coins(sender, recipient, coins, message=message)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_monetization_bp.route("/api/shop/gifts", methods=["GET"])
def gifts():
    try:
        user_id = request.args.get("user_id") or _uid()
        limit = min(int(request.args.get("limit", 50)), 200)
        return jsonify({"success": True, "user_id": user_id, **mon.list_gifts(user_id, limit=limit)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "sent": [], "received": []}), 500


# ---------------- Loyalty ----------------

@shop_monetization_bp.route("/api/shop/loyalty", methods=["GET"])
def loyalty():
    try:
        user_id = request.args.get("user_id") or _uid()
        return jsonify({"success": True, "user_id": user_id, "loyalty": mon.get_loyalty(user_id)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_monetization_bp.route("/api/shop/loyalty/redeem", methods=["POST"])
def loyalty_redeem():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _req_uid(data)
        reward_id = data.get("reward_id") or request.args.get("reward_id")
        if not reward_id:
            return jsonify({"success": False, "error": "reward_id is required"}), 400
        result = mon.redeem_loyalty(user_id, reward_id)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- Featured auction ----------------

@shop_monetization_bp.route("/api/shop/auction/feature", methods=["POST"])
def auction_feature():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _req_uid(data)
        listing_id = data.get("listing_id") or request.args.get("listing_id")
        method = (data.get("payment_method") or "coins").strip().lower()
        if not listing_id:
            return jsonify({"success": False, "error": "listing_id is required"}), 400
        result = mon.feature_listing(user_id, listing_id, payment_method=method)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_monetization_bp.route("/api/shop/auction/featured", methods=["GET"])
def auction_featured():
    try:
        return jsonify({"success": True, "featured_listing_ids": mon.get_featured_listing_ids()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "featured_listing_ids": []}), 500


# ---------------- Top 25 Legends collection ----------------

@shop_monetization_bp.route("/api/shop/top25/status", methods=["GET"])
def top25_status():
    try:
        user_id = request.args.get("user_id") or _uid()
        return jsonify({"success": True, "user_id": user_id, "top25": mon.get_top25_status(user_id)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@shop_monetization_bp.route("/api/shop/top25/claim", methods=["POST"])
def top25_claim():
    try:
        data = request.get_json(silent=True) or {}
        user_id = _req_uid(data)
        result = mon.claim_top25_completion(user_id)
        return jsonify(result), (200 if result.get("success") else 400)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
