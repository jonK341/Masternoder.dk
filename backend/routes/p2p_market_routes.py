"""P2P MN2↔coins market API."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

p2p_market_bp = Blueprint("p2p_market", __name__)


def _user_id() -> str:
    uid = (request.args.get("user_id") or "").strip()
    if not uid and request.is_json and request.json:
        uid = (request.json.get("user_id") or "").strip()
    return uid or "default_user"


@p2p_market_bp.route("/api/market/orders", methods=["GET"])
def market_orders():
    try:
        from backend.services.p2p_market_service import list_orders
        side = request.args.get("side")
        limit = request.args.get("limit", 50, type=int)
        return jsonify(list_orders(side=side, limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@p2p_market_bp.route("/api/market/trades", methods=["GET"])
def market_trades():
    try:
        from backend.services.p2p_market_service import list_recent_trades
        limit = request.args.get("limit", 20, type=int)
        return jsonify(list_recent_trades(limit=limit)), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@p2p_market_bp.route("/api/market/orders", methods=["POST"])
def market_create_order():
    body = request.get_json(silent=True) or {}
    from backend.services.p2p_market_service import create_order
    result = create_order(
        body.get("user_id") or _user_id(),
        body.get("side", ""),
        float(body.get("mn2_amount") or 0),
        float(body.get("price_coins_per_mn2") or 0),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@p2p_market_bp.route("/api/market/fill", methods=["POST"])
def market_fill():
    body = request.get_json(silent=True) or {}
    from backend.services.p2p_market_service import fill_order
    result = fill_order(
        body.get("user_id") or _user_id(),
        body.get("order_id", ""),
        body.get("mn2_amount"),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@p2p_market_bp.route("/api/market/cancel", methods=["POST"])
def market_cancel():
    body = request.get_json(silent=True) or {}
    from backend.services.p2p_market_service import cancel_order
    result = cancel_order(body.get("user_id") or _user_id(), body.get("order_id", ""))
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@p2p_market_bp.route("/api/market/config", methods=["GET"])
def market_config():
    """Public config for internal MN2 ↔ coins order book (trader agent liquidity)."""
    try:
        from backend.services.agent_trader_service import _market_cfg, list_strategies, trader_agent_ids
        cfg = _market_cfg()
        return jsonify({
            "success": True,
            "enabled": bool(cfg.get("enabled")),
            "quote_unit": "coins",
            "price_label": "coins per MN2",
            "trader_agent_count": len(trader_agent_ids()),
            "strategies": list_strategies(),
            "reference_price_coins_per_mn2": cfg.get("reference_price_coins_per_mn2"),
            "note": "Trader agents post sells and cross-buy on a schedule; users trade with unified coins.",
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@p2p_market_bp.route("/api/market/ticker", methods=["GET"])
def market_ticker():
    try:
        from backend.services.p2p_market_service import list_orders, list_recent_trades
        sells = list_orders(side="sell", limit=5).get("orders") or []
        buys = list_orders(side="buy", limit=5).get("orders") or []
        best_ask = sells[0]["price_coins_per_mn2"] if sells else None
        best_bid = buys[0]["price_coins_per_mn2"] if buys else None
        trades = list_recent_trades(limit=1).get("trades") or []
        last = trades[0] if trades else None
        return jsonify({
            "success": True,
            "best_ask": best_ask,
            "best_bid": best_bid,
            "sell_depth": len(sells),
            "buy_depth": len(buys),
            "last_trade": last,
            "last_price_coins_per_mn2": (
                round(float(last["coins"]) / float(last["mn2"]), 4)
                if last and last.get("mn2") and float(last["mn2"]) > 0
                else None
            ),
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
