"""Profit daemon 110 upgrades — batch 4 (items 11,19,21,23-25,33-35,37,50,67-71,77-79,86-87,94,99,101,103,108-109)."""
from __future__ import annotations

import json
import time

import pytest


def test_iceberg_splits():
    from backend.services.profit_daemon_ops_service import plan_iceberg_splits

    out = plan_iceberg_splits(notional_usd=200, max_chunk_usd=75)
    assert out.get("success")
    assert out.get("splits") >= 2
    assert sum(out.get("chunks_usd") or []) == pytest.approx(200, rel=0.01)


def test_ensemble_signal_blend():
    from backend.services.profit_daemon_ops_service import ensemble_signal_blend

    out = ensemble_signal_blend(spatial_bps=20, ai_bps=10, extended_bps=5)
    assert out.get("success")
    assert out.get("blend_bps") > 0


def test_venue_routing_score():
    from backend.services.profit_daemon_ops_service import venue_routing_score

    assert venue_routing_score("binance") > venue_routing_score("xeggex")


def test_risk_adjusted_notional():
    from backend.services.profit_daemon_ops_service import risk_adjusted_notional_usd

    out = risk_adjusted_notional_usd(base_usd=100, volatility_score=10, hit_rate_pct=60)
    assert out.get("success")
    assert out.get("adjusted_usd") >= 10


def test_treasury_stash_buckets():
    from backend.services.profit_daemon_ops_service import treasury_stash_buckets

    out = treasury_stash_buckets()
    assert out.get("success")
    assert "usd_live" in (out.get("buckets") or {})


def test_prefer_usdc_route():
    from backend.services.profit_daemon_ops_service import prefer_usdc_vs_usdt_route

    out = prefer_usdc_vs_usdt_route("binance", "nonkyc")
    assert out.get("preferred_quote") in ("USDC", "USDT")


def test_treasury_ledger_reconciliation():
    from backend.services.profit_daemon_ops_service import treasury_ledger_reconciliation

    out = treasury_ledger_reconciliation()
    assert out.get("success")
    assert "drift_usd" in out


def test_search_index_export():
    from backend.services.profit_daemon_ops_service import search_index_export

    out = search_index_export(limit=5)
    assert out.get("success") is not None


def test_pair_search_score_decomposition():
    from backend.services.profit_daemon_ops_service import pair_search_score_decomposition

    hit = {"symbol": "DOGE", "avg_net_bps": 15, "live_score": 12, "hit_rate_pct": 40, "search_score": 30}
    out = pair_search_score_decomposition(hit)
    assert out.get("success")
    assert "ledger_part" in (out.get("components") or {})


def test_skip_reason_trend_export():
    from backend.services.profit_daemon_ops_service import skip_reason_trend_export

    out = skip_reason_trend_export(hours=24)
    assert out.get("success")


def test_ppp_export_redacted():
    from backend.services.profit_daemon_ops_service import ppp_export_redacted

    out = ppp_export_redacted(hours=24)
    assert out.get("success")
    assert out.get("redacted") is True


def test_validate_payout_tax_id(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import profit_daemon_ops_service as ops

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    payout = data / "payout_config.json"
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ops, "_PAYOUT_PATH", str(payout))
    ex._write_json(str(payout), {"tax_id": "DK12345678"})
    out = ops.validate_payout_tax_id()
    assert out.get("valid") is True
    assert out.get("tax_id_set") is True


def test_mask_venue_balances():
    from backend.services.profit_daemon_ops_service import mask_venue_balances

    masked = mask_venue_balances({"binance": {"ok": True, "usdc": 100.5}})
    assert masked["binance"]["usdc"] == "masked"


def test_heartbeat_hmac_roundtrip(monkeypatch):
    from backend.services.profit_daemon_ops_service import sign_heartbeat_hmac, verify_heartbeat_hmac

    monkeypatch.setenv("PROFIT_HEARTBEAT_HMAC_SECRET", "test-secret")
    payload = {"updated_at": "2026-01-01T00:00:00Z", "loop": "exchange"}
    sig = sign_heartbeat_hmac(payload)
    assert sig
    assert verify_heartbeat_hmac(payload, sig) is True
    assert verify_heartbeat_hmac(payload, "bad") is False


def test_require_profit_daemon_admin(monkeypatch):
    from backend.services.profit_daemon_ops_service import require_profit_daemon_admin

    monkeypatch.delenv("PROFIT_DAEMON_ADMIN_KEY", raising=False)
    ok, _ = require_profit_daemon_admin({})
    assert ok is True
    monkeypatch.setenv("PROFIT_DAEMON_ADMIN_KEY", "sekret")
    ok, reason = require_profit_daemon_admin({"X-Profit-Daemon-Admin": "wrong"})
    assert ok is False
    ok, _ = require_profit_daemon_admin({"X-Profit-Daemon-Admin": "sekret"})
    assert ok is True


def test_profile_exchange_tick():
    from backend.services.profit_daemon_ops_service import profile_exchange_tick

    out = profile_exchange_tick(time.time() - 5)
    assert out.get("success")
    assert out.get("warn") is False


def test_worker_thread_health():
    from backend.services.profit_daemon_ops_service import worker_thread_health
    import threading

    alive = threading.Thread(target=lambda: None, name="test-alive")
    alive.start()
    alive.join()
    health = worker_thread_health([alive])
    assert "dead" in health


def test_arb_force_attempt_gate():
    from backend.services.profit_daemon_ops_service import arb_force_attempt_gate

    out = arb_force_attempt_gate({"platform": {"results": {"arbitrage": {}}}})
    assert out.get("skipped")


def test_run_exchange_tick_ops_batch4():
    from backend.services.profit_daemon_ops_service import run_exchange_tick_ops

    out = run_exchange_tick_ops({"platform": {"profit_pair_search": {"hits": []}}})
    assert out.get("success")
    assert "catalog_refresh" in out
    assert "tick_profile" in out
    assert "paypal_sweep" in out


def test_batch4_routes():
    from backend.routes.profit_daemon_routes import profit_daemon_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(profit_daemon_bp)
    client = app.test_client()
    for path in (
        "/api/profit-daemon/search-export?limit=5",
        "/api/profit-daemon/ensemble-blend",
        "/api/profit-daemon/treasury-buckets",
        "/api/profit-daemon/catalog-cache",
        "/api/profit-daemon/iceberg-plan?notional_usd=150",
        "/api/profit-daemon/heartbeat-preflight",
        "/api/profit-daemon/metrics-public",
    ):
        rv = client.get(path)
        assert rv.status_code == 200, path


def test_reload_config_admin_gate(monkeypatch):
    from backend.routes.profit_daemon_routes import profit_daemon_bp
    from flask import Flask

    monkeypatch.setenv("PROFIT_DAEMON_ADMIN_KEY", "admin-key")
    app = Flask(__name__)
    app.register_blueprint(profit_daemon_bp)
    client = app.test_client()
    rv = client.post("/api/profit-daemon/reload-config")
    assert rv.status_code == 403
    rv = client.post("/api/profit-daemon/reload-config", headers={"X-Profit-Daemon-Admin": "admin-key"})
    assert rv.status_code == 200
