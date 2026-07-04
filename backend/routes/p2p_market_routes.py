"""Internal MN2 ↔ coins order book API (Phase 3)."""
from flask import Blueprint, jsonify, request

from backend.services.account_resolution_service import resolve_user_id
from backend.services import p2p_market_service as market

p2p_market_bp = Blueprint("p2p_market", __name__)


def _uid(from_body: bool = False) -> str:
    if from_body:
        data = request.get_json(silent=True) or {}
        if data.get("user_id"):
            return str(data["user_id"]).strip()
    return resolve_user_id(from_body=from_body, from_query=True)


def _ticker() -> dict:
    sells = market.list_orders(side="sell", limit=200).get("orders") or []
    buys = market.list_orders(side="buy", limit=200).get("orders") or []
    best_ask = min((float(o.get("price_coins_per_mn2") or 0) for o in sells), default=None) if sells else None
    best_bid = max((float(o.get("price_coins_per_mn2") or 0) for o in buys), default=None) if buys else None
    sell_depth = sum(float(o.get("remaining_mn2") or o.get("mn2_amount") or 0) for o in sells)
    trades = market.list_recent_trades(limit=1).get("trades") or []
    last = None
    if trades:
        t = trades[0]
        mn2 = float(t.get("mn2") or 0)
        coins = float(t.get("coins") or 0)
        if mn2 > 0:
            last = coins / mn2
    return {
        "success": True,
        "best_ask": best_ask,
        "best_bid": best_bid,
        "sell_depth": sell_depth,
        "last_price_coins_per_mn2": last,
    }


@p2p_market_bp.route("/api/market/config", methods=["GET"])
def market_config():
    import json
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "mn2_config.json")
    cfg = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    ref = float(cfg.get("coins_per_mn2") or 100)
    return jsonify({
        "success": True,
        "enabled": True,
        "reference_price_coins_per_mn2": ref,
        "pair": "MN2/COINS",
    })


@p2p_market_bp.route("/api/market/ticker", methods=["GET"])
def market_ticker():
    return jsonify(_ticker())


@p2p_market_bp.route("/api/market/orders", methods=["GET"])
def market_orders():
    side = request.args.get("side")
    limit = int(request.args.get("limit") or 50)
    return jsonify(market.list_orders(side=side, limit=limit))


@p2p_market_bp.route("/api/market/trades", methods=["GET"])
def market_trades():
    limit = int(request.args.get("limit") or 20)
    return jsonify(market.list_recent_trades(limit=limit))


@p2p_market_bp.route("/api/market/orders", methods=["POST"])
def market_create_order():
    data = request.get_json(silent=True) or {}
    uid = _uid(from_body=True)
    return jsonify(market.create_order(
        uid,
        data.get("side"),
        float(data.get("mn2_amount") or 0),
        float(data.get("price_coins_per_mn2") or 0),
    ))


@p2p_market_bp.route("/api/market/fill", methods=["POST"])
def market_fill():
    data = request.get_json(silent=True) or {}
    uid = _uid(from_body=True)
    amt = data.get("mn2_amount")
    return jsonify(market.fill_order(uid, data.get("order_id"), float(amt) if amt is not None else None))


@p2p_market_bp.route("/api/market/cancel", methods=["POST"])
def market_cancel():
    data = request.get_json(silent=True) or {}
    uid = _uid(from_body=True)
    return jsonify(market.cancel_order(uid, data.get("order_id")))
