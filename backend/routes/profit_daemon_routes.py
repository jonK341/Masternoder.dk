"""Profit daemon monitor API — status, news, rentals."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

profit_daemon_bp = Blueprint("profit_daemon", __name__)


@profit_daemon_bp.route("/api/profit-daemon/metrics", methods=["GET"])
def profit_daemon_metrics():
    from backend.services.profit_daemon_ops_service import daemon_metrics_snapshot, metrics_ip_allowed
    from flask import request
    ip_check = metrics_ip_allowed(request.remote_addr)
    if ip_check.get("enforced") and not ip_check.get("allowed"):
        return jsonify({"success": False, "error": "ip_not_allowed", **ip_check}), 403
    return jsonify(daemon_metrics_snapshot())


@profit_daemon_bp.route("/api/profit-daemon/reload-config", methods=["POST"])
def profit_daemon_reload_config():
    from backend.services.profit_daemon_ops_service import reload_ppp_config, require_profit_daemon_admin
    ok, reason = require_profit_daemon_admin(dict(request.headers))
    if not ok:
        return jsonify({"success": False, "error": reason}), 403
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


@profit_daemon_bp.route("/api/profit-daemon/search-export", methods=["GET"])
def profit_daemon_search_export():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import search_index_export
    limit = request.args.get("limit", 50, type=int)
    return jsonify(search_index_export(limit=limit))


@profit_daemon_bp.route("/api/profit-daemon/score-decomposition", methods=["GET"])
def profit_daemon_score_decomposition():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import pair_search_score_decomposition
    from backend.services.exchange_profit_pair_search_service import read_index
    sym = (request.args.get("symbol") or "").upper()
    hits = read_index().get("hits") or []
    hit = next((h for h in hits if str(h.get("symbol") or "").upper() == sym), hits[0] if hits else {})
    return jsonify(pair_search_score_decomposition(hit or {}))


@profit_daemon_bp.route("/api/profit-daemon/ensemble-blend", methods=["GET"])
def profit_daemon_ensemble_blend():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import ensemble_signal_blend
    return jsonify(ensemble_signal_blend(
        spatial_bps=request.args.get("spatial_bps", 15.0, type=float),
        ai_bps=request.args.get("ai_bps", 10.0, type=float),
        extended_bps=request.args.get("extended_bps", 8.0, type=float),
    ))


@profit_daemon_bp.route("/api/profit-daemon/risk-notional", methods=["GET"])
def profit_daemon_risk_notional():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import risk_adjusted_notional_usd
    return jsonify(risk_adjusted_notional_usd(
        base_usd=request.args.get("base_usd", 75.0, type=float),
        volatility_score=request.args.get("volatility_score", 5.0, type=float),
        hit_rate_pct=request.args.get("hit_rate_pct", 40.0, type=float),
    ))


@profit_daemon_bp.route("/api/profit-daemon/treasury-buckets", methods=["GET"])
def profit_daemon_treasury_buckets():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import treasury_stash_buckets
    return jsonify(treasury_stash_buckets())


@profit_daemon_bp.route("/api/profit-daemon/quote-route", methods=["GET"])
def profit_daemon_quote_route():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import prefer_usdc_vs_usdt_route
    return jsonify(prefer_usdc_vs_usdt_route(
        request.args.get("buy_venue", "binance"),
        request.args.get("sell_venue", "nonkyc"),
    ))


@profit_daemon_bp.route("/api/profit-daemon/treasury-reconcile", methods=["GET"])
def profit_daemon_treasury_reconcile():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import treasury_ledger_reconciliation
    return jsonify(treasury_ledger_reconciliation())


@profit_daemon_bp.route("/api/profit-daemon/catalog-cache", methods=["GET"])
def profit_daemon_catalog_cache():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import read_shared_catalog_cache
    return jsonify(read_shared_catalog_cache())


@profit_daemon_bp.route("/api/profit-daemon/skip-trends", methods=["GET"])
def profit_daemon_skip_trends():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import skip_reason_trend_export
    hours = request.args.get("hours", 24, type=float)
    return jsonify(skip_reason_trend_export(hours=hours))


@profit_daemon_bp.route("/api/profit-daemon/ppp-cached", methods=["GET"])
def profit_daemon_ppp_cached():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import ppp_24h_snapshot_cached
    hours = request.args.get("hours", 24, type=float)
    return jsonify(ppp_24h_snapshot_cached(hours=hours))


@profit_daemon_bp.route("/api/profit-daemon/ppp-redacted", methods=["GET"])
def profit_daemon_ppp_redacted():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import ppp_export_redacted
    hours = request.args.get("hours", 24, type=float)
    return jsonify(ppp_export_redacted(hours=hours))


@profit_daemon_bp.route("/api/profit-daemon/iceberg-plan", methods=["GET"])
def profit_daemon_iceberg_plan():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import plan_iceberg_splits
    return jsonify(plan_iceberg_splits(
        notional_usd=request.args.get("notional_usd", 200.0, type=float),
        max_chunk_usd=request.args.get("max_chunk_usd", 75.0, type=float),
    ))


@profit_daemon_bp.route("/api/profit-daemon/metrics-public", methods=["GET"])
def profit_daemon_metrics_public():
    from backend.services.profit_daemon_ops_service import daemon_metrics_snapshot_public, verify_monitor_public_token
    from flask import request
    token = request.args.get("token")
    auth = verify_monitor_public_token(token)
    if auth.get("public_enabled") and not auth.get("authorized"):
        return jsonify({"success": False, "error": "invalid_token"}), 403
    return jsonify(daemon_metrics_snapshot_public())


@profit_daemon_bp.route("/api/profit-daemon/venue-balances-parallel", methods=["GET"])
def profit_daemon_venue_balances_parallel():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import parallel_venue_balances
    raw = request.args.get("venues", "binance,nonkyc,xeggex")
    ids = [v.strip() for v in raw.split(",") if v.strip()]
    return jsonify(parallel_venue_balances(ids))


@profit_daemon_bp.route("/api/profit-daemon/heartbeat-preflight", methods=["GET"])
def profit_daemon_heartbeat_preflight():
    from backend.services.profit_daemon_ops_service import heartbeat_host_preflight
    return jsonify(heartbeat_host_preflight())


@profit_daemon_bp.route("/api/profit-daemon/tax-id-validation", methods=["GET"])
def profit_daemon_tax_id_validation():
    from backend.services.profit_daemon_ops_service import validate_payout_tax_id
    return jsonify(validate_payout_tax_id())


@profit_daemon_bp.route("/api/profit-daemon/post-deploy-verify", methods=["GET"])
def profit_daemon_post_deploy_verify():
    from backend.services.profit_daemon_ops_service import post_deploy_verify_hook
    return jsonify(post_deploy_verify_hook())


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


@profit_daemon_bp.route("/api/profit-daemon/rental-overlay", methods=["GET"])
def profit_daemon_rental_overlay():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import apply_rental_symbol_overlay
    return jsonify(apply_rental_symbol_overlay())


@profit_daemon_bp.route("/api/profit-daemon/ai-skip-groups", methods=["GET"])
def profit_daemon_ai_skip_groups():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import ai_skip_reason_tile_groups
    hours = request.args.get("hours", 24, type=float)
    return jsonify(ai_skip_reason_tile_groups(hours=hours))


@profit_daemon_bp.route("/api/profit-daemon/agent-cooldown", methods=["GET"])
def profit_daemon_agent_cooldown():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import agent_skill_cooldown_check
    agent_id = request.args.get("agent_id", "ai_trader")
    skill_id = request.args.get("skill_id", "")
    return jsonify(agent_skill_cooldown_check(agent_id, skill_id=skill_id))


@profit_daemon_bp.route("/api/profit-daemon/sentiment-weight", methods=["GET"])
def profit_daemon_sentiment_weight():
    from backend.services.profit_daemon_ops_service import sentiment_feed_weight
    return jsonify(sentiment_feed_weight())


@profit_daemon_bp.route("/api/profit-daemon/ai-skill-profiles", methods=["GET"])
def profit_daemon_ai_skill_profiles():
    from backend.services.profit_daemon_ops_service import ai_skill_profile_sets
    profile = request.args.get("profile")
    return jsonify(ai_skill_profile_sets(profile=profile))


@profit_daemon_bp.route("/api/profit-daemon/stash-history", methods=["GET"])
def profit_daemon_stash_history():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import stash_history_series
    limit = request.args.get("limit", 48, type=int)
    return jsonify(stash_history_series(limit=limit))


@profit_daemon_bp.route("/api/profit-daemon/mn2-stash-mirror", methods=["GET"])
def profit_daemon_mn2_stash_mirror():
    from backend.services.profit_daemon_ops_service import mn2_stash_mirror
    return jsonify(mn2_stash_mirror())


@profit_daemon_bp.route("/api/profit-daemon/paypal-split", methods=["GET"])
def profit_daemon_paypal_split():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import plan_paypal_split_recipients
    amount = request.args.get("amount_usd", type=float)
    return jsonify(plan_paypal_split_recipients(amount_usd=amount))


@profit_daemon_bp.route("/api/profit-daemon/mobile-layout", methods=["GET"])
def profit_daemon_mobile_layout():
    from backend.services.profit_daemon_ops_service import mobile_stat_card_meta
    return jsonify(mobile_stat_card_meta())


@profit_daemon_bp.route("/api/profit-daemon/blue-green", methods=["POST"])
def profit_daemon_blue_green():
    from backend.services.profit_daemon_ops_service import blue_green_profile_switch, require_profit_daemon_admin
    ok, reason = require_profit_daemon_admin(dict(request.headers))
    if not ok:
        return jsonify({"success": False, "error": reason}), 403
    body = request.get_json(silent=True) or {}
    return jsonify(blue_green_profile_switch(target=body.get("profile")))


@profit_daemon_bp.route("/api/profit-daemon/weekly-report", methods=["GET"])
def profit_daemon_weekly_report():
    from backend.services.profit_daemon_ops_service import maybe_weekly_ppp_report
    return jsonify(maybe_weekly_ppp_report())


@profit_daemon_bp.route("/api/profit-daemon/ab-compare", methods=["GET"])
def profit_daemon_ab_compare():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import ab_strategy_profile_compare
    return jsonify(ab_strategy_profile_compare())


@profit_daemon_bp.route("/api/profit-daemon/backtest-replay", methods=["GET"])
def profit_daemon_backtest_replay():
    blocked = _rate_limit_check()
    if blocked:
        return blocked
    from backend.services.profit_daemon_ops_service import ppp_ledger_backtest_replay
    return jsonify(ppp_ledger_backtest_replay(
        hours=request.args.get("hours", 24, type=float),
        notional_usd=request.args.get("notional_usd", 75.0, type=float),
    ))


@profit_daemon_bp.route("/api/profit-daemon/jupyter-template", methods=["GET"])
def profit_daemon_jupyter_template():
    from backend.services.profit_daemon_ops_service import jupyter_ppp_template_path
    from flask import send_file
    info = jupyter_ppp_template_path()
    if info.get("exists"):
        return send_file(info["path"], mimetype="application/json", as_attachment=True,
                        download_name="ppp_analysis_template.ipynb")
    return jsonify(info)


@profit_daemon_bp.route("/api/profit-daemon/route-leaderboard", methods=["GET"])
def profit_daemon_route_leaderboard():
    from backend.services.profit_daemon_ops_service import anonymized_route_leaderboard, research_api_quota_check
    key = request.headers.get("X-Research-Key") or request.args.get("operator_key") or request.remote_addr
    quota = research_api_quota_check(key)
    if not quota.get("allowed"):
        return jsonify({"success": False, "error": "quota_exceeded", **quota}), 429
    limit = request.args.get("limit", 15, type=int)
    out = anonymized_route_leaderboard(limit=limit)
    out["quota"] = quota
    return jsonify(out)


@profit_daemon_bp.route("/api/profit-daemon/fill-streak-bonus", methods=["GET"])
def profit_daemon_fill_streak_bonus():
    from backend.services.profit_daemon_ops_service import maybe_mn2_fill_streak_bonus
    return jsonify(maybe_mn2_fill_streak_bonus({"platform": {"results": {"arbitrage": {}}}}))


@profit_daemon_bp.route("/api/profit-daemon/readiness-cta", methods=["GET"])
def profit_daemon_readiness_cta():
    from backend.services.profit_daemon_ops_service import exchange_readiness_cta
    return jsonify(exchange_readiness_cta())


@profit_daemon_bp.route("/api/profit-daemon/rental-trial", methods=["GET"])
def profit_daemon_rental_trial():
    from backend.services.profit_daemon_ops_service import rental_trial_eligibility
    user_id = request.args.get("user_id", "platform")
    return jsonify(rental_trial_eligibility(user_id=user_id))


@profit_daemon_bp.route("/api/profit-daemon/lazy-monitor", methods=["GET"])
def profit_daemon_lazy_monitor():
    from backend.services.profit_daemon_ops_service import lazy_monitor_poll
    return jsonify(lazy_monitor_poll())


@profit_daemon_bp.route("/api/profit-daemon/async-backend", methods=["GET"])
def profit_daemon_async_backend():
    from backend.services.profit_daemon_ops_service import evaluate_async_loop_backend
    return jsonify(evaluate_async_loop_backend())


@profit_daemon_bp.route("/api/profit-daemon/purge-payout-history", methods=["POST"])
def profit_daemon_purge_payout_history():
    from backend.services.profit_daemon_ops_service import purge_payout_history, require_profit_daemon_admin
    ok, reason = require_profit_daemon_admin(dict(request.headers))
    if not ok:
        return jsonify({"success": False, "error": reason}), 403
    body = request.get_json(silent=True) or {}
    return jsonify(purge_payout_history(
        older_than_days=int(body.get("older_than_days") or 365),
        dry_run=body.get("dry_run", True),
    ))


@profit_daemon_bp.route("/api/profit-daemon/upgrades-state", methods=["GET"])
def profit_daemon_upgrades_state():
    from backend.services.profit_daemon_ops_service import profit_upgrades_state
    return jsonify(profit_upgrades_state())


@profit_daemon_bp.route("/api/profit-daemon/ppp-narrative", methods=["GET"])
def profit_daemon_ppp_narrative():
    from backend.services.profit_daemon_ops_service import ppp_summary_llm_narrative
    from backend.services.profit_daemon_monitor_service import _light_ppp_snapshot
    return jsonify(ppp_summary_llm_narrative(_light_ppp_snapshot(hours=24)))
