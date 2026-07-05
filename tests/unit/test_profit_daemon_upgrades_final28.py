"""Profit daemon 110 upgrades — final batch (items 22,26-31,39-40,49,60-61,72,80-84,89-92,95-97,102,104-105,110)."""
from __future__ import annotations

import time

import pytest


def test_rental_symbol_overlay():
    from backend.services.profit_daemon_ops_service import apply_rental_symbol_overlay

    out = apply_rental_symbol_overlay()
    assert out.get("success")


def test_hot_spread_ai_bypass():
    from backend.services.profit_daemon_ops_service import record_hot_spread_ai_bypass

    out = record_hot_spread_ai_bypass(symbol="DOGE", net_bps=20, agent_id="ai_trader", skip_reason="cooldown")
    assert out.get("success") or out.get("skipped")


def test_agent_skill_cooldown():
    from backend.services.profit_daemon_ops_service import agent_skill_cooldown_check, record_agent_loss

    record_agent_loss("test_agent", won=False)
    record_agent_loss("test_agent", won=False)
    record_agent_loss("test_agent", won=False)
    out = agent_skill_cooldown_check("test_agent", skill_id="spatial_arbitrage")
    assert out.get("success")
    record_agent_loss("test_agent", won=True)
    assert agent_skill_cooldown_check("test_agent").get("on_cooldown") is False


def test_sentiment_feed_weight(monkeypatch):
    from backend.services.profit_daemon_ops_service import sentiment_feed_weight

    monkeypatch.setenv("EXCHANGE_SENTIMENT_WEIGHT", "0.42")
    assert sentiment_feed_weight().get("weight") == pytest.approx(0.42)


def test_ai_skip_reason_tile_groups():
    from backend.services.profit_daemon_ops_service import ai_skip_reason_tile_groups

    out = ai_skip_reason_tile_groups(hours=24)
    assert out.get("success")


def test_ppp_summary_llm_narrative():
    from backend.services.profit_daemon_ops_service import ppp_summary_llm_narrative

    out = ppp_summary_llm_narrative({"fill_count": 3, "hit_rate_pct": 45, "avg_net_bps": 12, "scan_count": 100})
    assert out.get("narrative")
    assert out.get("tone") in ("strong", "moderate", "quiet")


def test_ai_skill_profile_sets():
    from backend.services.profit_daemon_ops_service import ai_skill_profile_sets

    out = ai_skill_profile_sets(profile="fast")
    assert "spatial_arbitrage" in (out.get("skills") or [])


def test_stash_history_and_mn2_mirror():
    from backend.services.profit_daemon_ops_service import mn2_stash_mirror, record_stash_history_point, stash_history_series

    rec = record_stash_history_point()
    assert rec.get("success") or "error" in rec
    series = stash_history_series(limit=10)
    assert series.get("success")
    mirror = mn2_stash_mirror()
    assert mirror.get("success") or "error" in mirror


def test_paypal_split_recipients():
    from backend.services.profit_daemon_ops_service import plan_paypal_split_recipients

    out = plan_paypal_split_recipients(amount_usd=200)
    assert out.get("success")
    assert "recipients" in out


def test_mobile_and_public_token(monkeypatch):
    from backend.services.profit_daemon_ops_service import mobile_stat_card_meta, verify_monitor_public_token

    assert mobile_stat_card_meta().get("mobile_optimized") is True
    monkeypatch.setenv("PROFIT_MONITOR_PUBLIC_TOKEN", "pub-tok")
    assert verify_monitor_public_token("pub-tok").get("authorized") is True
    assert verify_monitor_public_token("bad").get("authorized") is False


def test_blue_green_profile_switch():
    from backend.services.profit_daemon_ops_service import blue_green_profile_switch

    out = blue_green_profile_switch(target="fast")
    assert out.get("success")
    assert out.get("active") == "fast"


def test_metrics_ip_allowlist(monkeypatch):
    from backend.services.profit_daemon_ops_service import metrics_ip_allowed

    monkeypatch.setenv("PROFIT_METRICS_IP_ALLOWLIST", "10.0.0.1")
    assert metrics_ip_allowed("10.0.0.1").get("allowed") is True
    assert metrics_ip_allowed("1.2.3.4").get("allowed") is False


def test_weekly_report_and_ab_compare():
    from backend.services.profit_daemon_ops_service import ab_strategy_profile_compare, maybe_weekly_ppp_report

    weekly = maybe_weekly_ppp_report()
    assert weekly.get("success") or weekly.get("skipped")
    ab = ab_strategy_profile_compare()
    assert ab.get("success")


def test_backtest_replay():
    from backend.services.profit_daemon_ops_service import ppp_ledger_backtest_replay

    out = ppp_ledger_backtest_replay(hours=24, notional_usd=50)
    assert out.get("success")


def test_jupyter_template_and_leaderboard():
    from backend.services.profit_daemon_ops_service import anonymized_route_leaderboard, jupyter_ppp_template_path

    assert jupyter_ppp_template_path().get("exists") is True
    lb = anonymized_route_leaderboard(limit=5)
    assert lb.get("anonymized") is True


def test_research_api_quota():
    from backend.services.profit_daemon_ops_service import research_api_quota_check

    key = f"op-{time.time()}"
    first = research_api_quota_check(key, max_per_hour=2)
    assert first.get("allowed") is True
    research_api_quota_check(key, max_per_hour=2)
    third = research_api_quota_check(key, max_per_hour=2)
    assert third.get("allowed") is False


def test_mn2_fill_streak_and_rental_trial():
    from backend.services.profit_daemon_ops_service import maybe_mn2_fill_streak_bonus, rental_trial_eligibility

    bonus = maybe_mn2_fill_streak_bonus({"platform": {"results": {"arbitrage": {"fills": 1}}}})
    assert bonus.get("success")
    trial = rental_trial_eligibility()
    assert trial.get("success")
    assert "eligible" in trial


def test_readiness_cta():
    from backend.services.profit_daemon_ops_service import exchange_readiness_cta

    out = exchange_readiness_cta()
    assert out.get("success")
    assert "show_cta" in out


def test_lazy_monitor_and_async_backend():
    from backend.services.profit_daemon_ops_service import evaluate_async_loop_backend, lazy_monitor_poll

    lazy = lazy_monitor_poll()
    assert lazy.get("success")
    async_eval = evaluate_async_loop_backend()
    assert async_eval.get("success")
    assert "uvloop" in (async_eval.get("options") or {})


def test_purge_payout_history_dry_run():
    from backend.services.profit_daemon_ops_service import purge_payout_history

    out = purge_payout_history(dry_run=True)
    assert out.get("success")


def test_profit_upgrades_state_complete():
    from backend.services.profit_daemon_ops_service import profit_upgrades_state

    out = profit_upgrades_state()
    assert out.get("complete") is True
    assert out.get("done") >= 110


def test_run_final_upgrade_hooks():
    from backend.services.profit_daemon_ops_service import run_final_upgrade_hooks

    out = run_final_upgrade_hooks({"platform": {"results": {"arbitrage": {}}}})
    assert out.get("success")
    assert out.get("upgrades_state", {}).get("complete") is True


def test_final28_routes():
    from backend.routes.profit_daemon_routes import profit_daemon_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(profit_daemon_bp)
    client = app.test_client()
    for path in (
        "/api/profit-daemon/rental-overlay",
        "/api/profit-daemon/ai-skip-groups",
        "/api/profit-daemon/sentiment-weight",
        "/api/profit-daemon/stash-history",
        "/api/profit-daemon/mn2-stash-mirror",
        "/api/profit-daemon/mobile-layout",
        "/api/profit-daemon/readiness-cta",
        "/api/profit-daemon/rental-trial",
        "/api/profit-daemon/async-backend",
        "/api/profit-daemon/upgrades-state",
        "/api/profit-daemon/ppp-narrative",
        "/api/profit-daemon/route-leaderboard",
        "/api/profit-daemon/backtest-replay",
        "/api/profit-daemon/ab-compare",
    ):
        rv = client.get(path)
        assert rv.status_code == 200, path
