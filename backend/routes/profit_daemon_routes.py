"""Profit daemon monitor API — status, news, rentals."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

profit_daemon_bp = Blueprint("profit_daemon", __name__)


@profit_daemon_bp.route("/api/profit-daemon/metrics", methods=["GET"])
def profit_daemon_metrics():
    from backend.services.profit_daemon_ops_service import daemon_metrics_snapshot
    return jsonify(daemon_metrics_snapshot())


@profit_daemon_bp.route("/api/profit-daemon/reload-config", methods=["POST"])
def profit_daemon_reload_config():
    from backend.services.profit_daemon_ops_service import reload_ppp_config
    return jsonify(reload_ppp_config())


@profit_daemon_bp.route("/api/profit-daemon/ppp/timeseries", methods=["GET"])
def profit_daemon_ppp_timeseries():
    from backend.services.profit_daemon_ops_service import ppp_timeseries_export
    hours = request.args.get("hours", 24, type=float)
    return jsonify(ppp_timeseries_export(hours=hours))


@profit_daemon_bp.route("/api/profit-daemon/search/volatility-windows", methods=["GET"])
def profit_daemon_volatility_windows():
    from backend.services.exchange_profit_pair_search_service import volatility_window_scores
    symbol = (request.args.get("symbol") or "DOGE").upper()
    return jsonify({"success": True, "symbol": symbol, "windows": volatility_window_scores(symbol)})


@profit_daemon_bp.route("/api/profit-daemon/reload-connectors", methods=["POST"])
def profit_daemon_reload_connectors():
    from backend.services.profit_daemon_ops_service import reload_connectors_config
    return jsonify(reload_connectors_config())


@profit_daemon_bp.route("/api/profit-daemon/triangular-gate", methods=["GET"])
def profit_daemon_triangular_gate():
    from backend.services.profit_daemon_ops_service import triangular_live_allowed
    return jsonify(triangular_live_allowed())


@profit_daemon_bp.route("/api/profit-daemon/status", methods=["GET"])
def profit_daemon_status():
    from backend.services.profit_daemon_monitor_service import monitor_status
    return jsonify(monitor_status())


@profit_daemon_bp.route("/api/profit-daemon/news", methods=["GET"])
def profit_daemon_news():
    from backend.routes.platform_news_routes import _load_news
    limit = request.args.get("limit", 12, type=int)
    items = [
        i for i in _load_news()
        if (i.get("channel") or i.get("category") or "").lower() == "profit"
    ]
    if limit > 0:
        items = items[:limit]
    return jsonify({"success": True, "news": items, "count": len(items)})


@profit_daemon_bp.route("/api/profit-daemon/rentals", methods=["GET"])
def profit_daemon_rentals():
    from backend.services.exchange_rental_service import rental_catalog
    cat = rental_catalog()
    rentals = [
        r for r in (cat.get("rentals") or [])
        if r.get("daemon")
    ]
    return jsonify({
        "success": True,
        "currency": cat.get("currency"),
        "rentals": rentals,
        "shop_href": "/exchange?tab=marketplace",
    })
