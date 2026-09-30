"""P2P MN2↔coins market API."""
from __future__ import annotations

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
    last_trade = None
    if trades:
        last_trade = trades[0]
        mn2 = float(last_trade.get("mn2") or 0)
        coins = float(last_trade.get("coins") or 0)
        if mn2 > 0:
            last = coins / mn2
    return {
        "success": True,
        "best_ask": best_ask,
        "best_bid": best_bid,
        "sell_depth": sell_depth,
        "buy_depth": len(buys),
        "last_trade": last_trade,
        "last_price_coins_per_mn2": last,
    }


@p2p_market_bp.route("/api/market/config", methods=["GET"])
def market_config():
    """Public config for internal MN2 ↔ coins order book (trader agent liquidity)."""
    try:
        from backend.services.agent_trader_service import _market_cfg, list_strategies, trader_agent_ids
        cfg = _market_cfg()
        ref = cfg.get("reference_price_coins_per_mn2")
        if ref is None:
            import json
            import os
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "mn2_config.json",
            )
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    mn2_cfg = json.load(f)
                ref = float(mn2_cfg.get("coins_per_mn2") or 100)
        return jsonify({
            "success": True,
            "enabled": bool(cfg.get("enabled")),
            "quote_unit": "coins",
            "price_label": "coins per MN2",
            "pair": "MN2/COINS",
            "trader_agent_count": len(trader_agent_ids()),
            "strategies": list_strategies(),
            "reference_price_coins_per_mn2": ref,
            "note": "Trader agents post sells and cross-buy on a schedule; users trade with unified coins.",
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


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
    result = market.create_order(
        uid,
        data.get("side"),
        float(data.get("mn2_amount") or 0),
        float(data.get("price_coins_per_mn2") or 0),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@p2p_market_bp.route("/api/market/fill", methods=["POST"])
def market_fill():
    data = request.get_json(silent=True) or {}
    uid = _uid(from_body=True)
    amt = data.get("mn2_amount")
    result = market.fill_order(uid, data.get("order_id"), float(amt) if amt is not None else None)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@p2p_market_bp.route("/api/market/cancel", methods=["POST"])
def market_cancel():
    data = request.get_json(silent=True) or {}
    uid = _uid(from_body=True)
    result = market.cancel_order(uid, data.get("order_id"))
    code = 200 if result.get("success") else 400
    return jsonify(result), code
