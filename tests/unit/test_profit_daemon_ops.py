"""Profit daemon ops — kill switch, alerts, auto-tune, metrics."""
from __future__ import annotations

import json
import os
import time

import pytest


@pytest.fixture
def pps_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import exchange_profit_pair_search_service as pps
    from backend.services import external_exchange_connector_service as conn

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    cfg_path = data / "profit_path_protocol.json"
    ledger_path = data / "profit_path_ledger.jsonl"
    index_path = data / "profit_pair_search_index.json"
    catalog_path = data / "profit_pair_catalog_cache.json"

    monkeypatch.setattr(ppp, "_CFG_PATH", str(cfg_path))
    monkeypatch.setattr(ppp, "_LEDGER_PATH", str(ledger_path))
    monkeypatch.setattr(pps, "_INDEX_PATH", str(index_path))
    monkeypatch.setattr(pps, "_CATALOG_CACHE_PATH", str(catalog_path))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(conn, "_PRICE_CACHE_PATH", str(data / "external_prices.json"))
    monkeypatch.setenv("EXCHANGE_PROFIT_PAIR_SEARCH", "1")
    ex._write_json(str(cfg_path), {
        "enabled": True,
        "profit_pair_search": {
            "enabled": True,
            "top_n": 5,
            "volatility_weight": 0.12,
            "triangular_bonus": 4.0,
        },
    })
    return {"pps": pps, "ppp": ppp}


def test_profit_kill_active(monkeypatch):
    from backend.services import profit_daemon_ops_service as ops

    monkeypatch.delenv("EXCHANGE_PROFIT_KILL", raising=False)
    assert ops.profit_kill_active() is False
    monkeypatch.setenv("EXCHANGE_PROFIT_KILL", "1")
    assert ops.profit_kill_active() is True
    block = ops.check_profit_kill(action="test")
    assert block and block.get("blocked")


def test_live_enabled_respects_kill(monkeypatch):
    from backend.services import exchange_arbitrage_service as arb

    monkeypatch.setenv("EXCHANGE_PROFIT_KILL", "1")
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    assert arb.live_enabled() is False


def test_ppp_reload_config(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import profit_daemon_ops_service as ops

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    cfg_path = data / "profit_path_protocol.json"
    monkeypatch.setattr(ppp, "_CFG_PATH", str(cfg_path))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    ex._write_json(str(cfg_path), {"enabled": True, "default_threshold_bps": 30})
    first = ppp.load_config()
    assert first["default_threshold_bps"] == 30
    ex._write_json(str(cfg_path), {"enabled": True, "default_threshold_bps": 22})
    out = ops.reload_ppp_config()
    assert out.get("success")
    third = ppp.load_config()
    assert third["default_threshold_bps"] == 22


def test_volatility_spread_score(pps_env):
    pps = pps_env["pps"]
    ppp = pps_env["ppp"]
    sym = "DOGE"
    for nb in (10.0, 20.0, 5.0, 25.0):
        opp = {
            "symbol": sym,
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "gross_bps": nb + 5,
            "fee_bps": 5.0,
            "net_bps": nb,
            "notional_usd": 25.0,
        }
        ppp.record_scan(agent_id="arb_test", best=opp, decision="scan", mode="paper")
    score = pps.volatility_spread_score(sym)
    assert score > 0


def test_triangular_symbol_bonus(pps_env, monkeypatch):
    pps = pps_env["pps"]
    monkeypatch.setattr(
        "backend.services.exchange_extended_profit_service._strategy_cfg",
        lambda name: {"loops": [["BTC", "ETH", "USDC"]]} if name == "triangular_paper" else {},
    )
    bonus = pps.triangular_symbol_bonus(["BTC", "XRP"])
    assert bonus.get("BTC", 0) > 0
    assert "XRP" not in bonus


def test_merge_rankings_volatility_bonus(pps_env, monkeypatch):
    pps = pps_env["pps"]
    monkeypatch.setattr(pps, "volatility_spread_score", lambda sym, **kw: 10.0 if sym == "DOGE" else 0.0)
    monkeypatch.setattr(pps, "triangular_symbol_bonus", lambda symbols=None: {"DOGE": 4.0})
    ledger = [{
        "symbol": "DOGE",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "avg_net_bps": 20.0,
        "hit_rate_pct": 50.0,
        "fill_count": 1,
        "last_profit_usd": 0.5,
    }]
    merged = pps._merge_rankings(ledger, [], top_n=5)
    assert merged[0]["volatility_score"] == 10.0
    assert merged[0].get("triangular") is True


def test_auto_tune_sweep_min(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import profit_daemon_ops_service as ops

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    payout = data / "payout_config.json"
    ledger = data / "treasury_stash_ledger.jsonl"
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ops, "_PAYOUT_PATH", str(payout))
    ex._write_json(str(payout), {"min_sweep_usd": 500, "auto_sweep_tiers": [
        {"stash_usd": 500, "min_sweep_usd": 100},
        {"stash_usd": 50, "min_sweep_usd": 50},
    ]})
    with open(ledger, "w", encoding="utf-8") as f:
        f.write(json.dumps({"amount_usd": 600, "mode": "live"}) + "\n")
    monkeypatch.setattr(
        "backend.services.profit_daemon_monitor_service._light_treasury_snapshot",
        lambda: {"live_stash_usd": 600},
    )
    out = ops.maybe_auto_tune_sweep_min()
    assert out.get("success")
    assert out.get("min_sweep_usd") == 100


def test_metrics_snapshot():
    from backend.services.profit_daemon_ops_service import daemon_metrics_snapshot

    snap = daemon_metrics_snapshot()
    assert snap.get("success") is True
    assert "profit_kill" in snap
    assert "ppp_24h" in snap


def test_profit_daemon_metrics_route():
    from backend.routes.profit_daemon_routes import profit_daemon_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(profit_daemon_bp)
    client = app.test_client()
    rv = client.get("/api/profit-daemon/metrics")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("success") is True


def test_rotate_daemon_logs(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import profit_daemon_ops_service as ops

    logs = tmp_path / "logs"
    logs.mkdir()
    log_file = logs / "profit_daemon_stdout.log"
    log_file.write_text("x" * 200, encoding="utf-8")
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(ops, "_STDOUT_LOG", str(log_file))
    monkeypatch.setenv("PROFIT_DAEMON_LOG_MAX_BYTES", "100")
    out = ops.rotate_daemon_logs()
    assert out.get("success")
    assert out.get("rotated")
    assert log_file.exists()
