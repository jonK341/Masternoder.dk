"""Profit daemon 110 upgrades — session 3 (items 15,18,20,32,36,38,45-47,59,75,85,88,98,100)."""
from __future__ import annotations

import time

import pytest


def test_symbol_alias_normalize():
    from backend.services.profit_daemon_ops_service import normalize_symbol_alias

    assert normalize_symbol_alias("1000SHIB") == "SHIB"
    assert normalize_symbol_alias("btc") == "BTC"


def test_ml_ranker_blend():
    from backend.services.profit_daemon_ops_service import ml_ranker_blend

    score = ml_ranker_blend(ledger_score=10.0, volatility_score=5.0, hit_rate_pct=50.0)
    assert score > 0


def test_defi_router_symbols():
    from backend.services.profit_daemon_ops_service import defi_router_symbols

    syms = defi_router_symbols()
    assert "UNI" in syms
    assert "AAVE" in syms


def test_compound_streak_tier():
    from backend.services.profit_daemon_ops_service import compound_streak_bonus_tier

    t = compound_streak_bonus_tier(7)
    assert t.get("bonus_pct") == 5


def test_compound_pause_on_kill(monkeypatch):
    from backend.services.profit_daemon_ops_service import compound_pause_on_kill

    monkeypatch.delenv("EXCHANGE_PROFIT_KILL", raising=False)
    assert compound_pause_on_kill().get("compound_paused") is False
    monkeypatch.setenv("EXCHANGE_PROFIT_KILL", "1")
    assert compound_pause_on_kill().get("compound_paused") is True


def test_sweep_dry_run_line():
    from backend.services.profit_daemon_ops_service import sweep_dry_run_line

    line = sweep_dry_run_line()
    assert "sweep_dry_run" in line


def test_partial_sweep_plan():
    from backend.services.profit_daemon_ops_service import plan_partial_sweep

    out = plan_partial_sweep(fraction=0.5)
    assert "success" in out


def test_top25_deeplinks():
    from backend.services.profit_daemon_ops_service import top25_blocker_deeplinks

    links = top25_blocker_deeplinks()
    assert links.get("success")
    assert len(links.get("anchors") or []) >= 3


def test_profit_api_rate_limit():
    from backend.services.profit_daemon_ops_service import profit_api_rate_limit

    key = f"test-{time.time()}"
    first = profit_api_rate_limit(key, max_per_min=2)
    assert first.get("allowed") is True
    profit_api_rate_limit(key, max_per_min=2)
    third = profit_api_rate_limit(key, max_per_min=2)
    assert third.get("allowed") is False


def test_venue_balance_cache_ttl():
    from backend.services.profit_daemon_ops_service import venue_balance_cache_ttl

    assert venue_balance_cache_ttl("binance") >= 1


def test_tick_budget():
    from backend.services.profit_daemon_ops_service import tick_budget_exceeded

    assert tick_budget_exceeded(time.time()) is False
    assert tick_budget_exceeded(time.time() - 120) is True


def test_run_exchange_tick_ops():
    from backend.services.profit_daemon_ops_service import run_exchange_tick_ops

    out = run_exchange_tick_ops({"platform": {"profit_pair_search": {"hits": []}}})
    assert out.get("success")
    assert "sweep_dry_run" in out
    assert "top25_sync" in out


def test_profit_daemon_new_routes():
    from backend.routes.profit_daemon_routes import profit_daemon_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(profit_daemon_bp)
    client = app.test_client()
    for path in (
        "/api/profit-daemon/symbol-aliases?symbol=1000SHIB",
        "/api/profit-daemon/compound-tier?streak=3",
        "/api/profit-daemon/top25-links",
        "/api/profit-daemon/defi-symbols",
    ):
        rv = client.get(path)
        assert rv.status_code == 200, path
        assert rv.get_json().get("success") is True


def test_merge_rankings_uses_alias(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import exchange_profit_pair_search_service as pps

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    monkeypatch.setattr(ppp, "_CFG_PATH", str(data / "profit_path_protocol.json"))
    monkeypatch.setattr(pps, "_INDEX_PATH", str(data / "profit_pair_search_index.json"))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    ex._write_json(str(data / "profit_path_protocol.json"), {"enabled": True, "profit_pair_search": {"enabled": True}})
    monkeypatch.setattr(pps, "volatility_spread_score", lambda sym, **kw: 1.0)
    monkeypatch.setattr(pps, "triangular_symbol_bonus", lambda symbols=None: {})
    monkeypatch.setattr(pps, "volatility_window_scores", lambda sym: {})
    ledger = [{
        "symbol": "1000SHIB",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "avg_net_bps": 15.0,
        "hit_rate_pct": 40.0,
        "fill_count": 2,
        "last_profit_usd": 0.1,
    }]
    merged = pps._merge_rankings(ledger, [], top_n=5)
    assert merged[0]["symbol"] == "SHIB"
