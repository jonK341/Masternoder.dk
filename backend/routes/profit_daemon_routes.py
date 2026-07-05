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


@profit_daemon_bp.route("/api/profit-daemon/force-attempt-budget", methods=["GET"])
def profit_daemon_force_attempt_budget():
    from backend.services.profit_daemon_ops_service import force_attempt_budget_state
    return jsonify(force_attempt_budget_state())


@profit_daemon_bp.route("/api/profit-daemon/venue-floors", methods=["GET"])
def profit_daemon_venue_floors():
    from backend.services.profit_daemon_ops_service import venue_min_notional_floors
    return jsonify(venue_min_notional_floors())


@profit_daemon_bp.route("/api/profit-daemon/paypal-tiers", methods=["GET"])
def profit_daemon_paypal_tiers():
    from backend.services.profit_daemon_ops_service import paypal_tier_presets
    return jsonify(paypal_tier_presets())


@profit_daemon_bp.route("/api/profit-daemon/paper-threshold", methods=["GET"])
def profit_daemon_paper_threshold():
    from backend.services.profit_daemon_ops_service import paper_unswept_threshold_display
    return jsonify(paper_unswept_threshold_display())


@profit_daemon_bp.route("/api/profit-daemon/tax-export", methods=["GET"])
def profit_daemon_tax_export():
    from backend.services.profit_daemon_ops_service import tax_export_csv
    season = request.args.get("season")
    return jsonify(tax_export_csv(season=season))


@profit_daemon_bp.route("/api/profit-daemon/loop-sparkline", methods=["GET"])
def profit_daemon_loop_sparkline():
    from backend.services.profit_daemon_ops_service import loop_sparkline_from_heartbeat
    return jsonify(loop_sparkline_from_heartbeat())


@profit_daemon_bp.route("/api/profit-daemon/spork-audit", methods=["GET"])
def profit_daemon_spork_audit():
    from backend.services.profit_daemon_ops_service import spork_gate_startup_audit
    return jsonify(spork_gate_startup_audit())


@profit_daemon_bp.route("/api/profit-daemon/casino-skip", methods=["GET"])
def profit_daemon_casino_skip():
    from backend.services.profit_daemon_ops_service import casino_agent_tick_skip_on_kill
    return jsonify(casino_agent_tick_skip_on_kill())


@profit_daemon_bp.route("/api/profit-daemon/paper-live-banner", methods=["GET"])
def profit_daemon_paper_live_banner():
    from backend.services.profit_daemon_ops_service import paper_live_separation_banner
    return jsonify(paper_live_separation_banner())


@profit_daemon_bp.route("/api/profit-daemon/payout-validation", methods=["GET"])
def profit_daemon_payout_validation():
    from backend.services.profit_daemon_ops_service import validate_payout_share_pct
    return jsonify(validate_payout_share_pct())


def _rate_limit_check():
    from backend.services.profit_daemon_ops_service import profit_api_rate_limit
    key = request.remote_addr or "local"
    rl = profit_api_rate_limit(key)
    if not rl.get("allowed"):
        return jsonify({"success": False, "error": "rate_limited", **rl}), 429
    return None


@profit_daemon_bp.route("/api/profit-daemon/symbol-aliases", methods=["GET"])
def profit_daemon_symbol_aliases():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import _SYMBOL_ALIASES, normalize_symbol_alias
    sym = request.args.get("symbol")
    if sym:
        return jsonify({"success": True, "symbol": sym.upper(), "normalized": normalize_symbol_alias(sym)})
    return jsonify({"success": True, "aliases": _SYMBOL_ALIASES})


@profit_daemon_bp.route("/api/profit-daemon/compound-tier", methods=["GET"])
def profit_daemon_compound_tier():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import compound_streak_bonus_tier
    streak = request.args.get("streak", 0, type=int)
    return jsonify(compound_streak_bonus_tier(streak))


@profit_daemon_bp.route("/api/profit-daemon/top25-links", methods=["GET"])
def profit_daemon_top25_links():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import top25_blocker_deeplinks
    return jsonify(top25_blocker_deeplinks())


@profit_daemon_bp.route("/api/profit-daemon/partial-sweep", methods=["GET"])
def profit_daemon_partial_sweep():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import plan_partial_sweep
    frac = request.args.get("fraction", 0.5, type=float)
    return jsonify(plan_partial_sweep(fraction=frac))


@profit_daemon_bp.route("/api/profit-daemon/binance-preflight", methods=["GET"])
def profit_daemon_binance_preflight():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import binance_withdraw_preflight
    return jsonify(binance_withdraw_preflight())


@profit_daemon_bp.route("/api/profit-daemon/defi-symbols", methods=["GET"])
def profit_daemon_defi_symbols():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import defi_router_symbols
    return jsonify({"success": True, "symbols": defi_router_symbols()})


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
