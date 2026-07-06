"""Profit daemon monitor API — status, news, rentals, instance heartbeat.

Two views of status:
- Public (no auth): operational health only — daemon online, loop ages,
  readiness, blockers, engine stats. No balances, payout amounts, treasury
  stash, host names, or instance detail.
- Owner (X-Exchange-Admin-Key header): the full payload, used by Business
  Control and the laptop control app.

POST /api/profit-daemon/heartbeat lets a remote (laptop) daemon instance
register itself so the monitor can detect double-tick conflicts.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

profit_daemon_bp = Blueprint("profit_daemon", __name__)


def _admin() -> bool:
    from backend.services.exchange_admin_auth import admin_authorized
    return admin_authorized()


@profit_daemon_bp.route("/api/profit-daemon/status", methods=["GET"])
def profit_daemon_status():
    from backend.services.profit_daemon_monitor_service import monitor_status, sanitize_status_public
    full = monitor_status()
    if _admin():
        full["view"] = "owner"
        return jsonify(full)
    return jsonify(sanitize_status_public(full))


@profit_daemon_bp.route("/api/profit-daemon/heartbeat", methods=["POST"])
def profit_daemon_heartbeat():
    if not _admin():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.profit_daemon_instance_service import report_instance
    data = request.get_json(silent=True) or {}
    return jsonify(report_instance(data))


@profit_daemon_bp.route("/api/profit-daemon/instances", methods=["GET"])
def profit_daemon_instances():
    if not _admin():
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.profit_daemon_instance_service import instances_summary
    return jsonify({"success": True, **instances_summary()})


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
