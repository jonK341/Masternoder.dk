"""Unit tests for technique executor + residual-edge helpers."""
from __future__ import annotations


def test_residual_edge_ok_passes_clean_spread():
    from backend.services.exchange_technique_executor_service import residual_edge_ok

    edge = residual_edge_ok(net_bps=40.0, mid_skew_bps=12.0, floor_bps=15.0)
    assert edge["ok"] is True
    assert edge["residual_bps"] == 28.0


def test_residual_edge_rejects_phantom_skew():
    from backend.services.exchange_technique_executor_service import residual_edge_ok

    edge = residual_edge_ok(net_bps=90.0, mid_skew_bps=88.0, floor_bps=15.0)
    assert edge["ok"] is False
    assert edge["reason"] == "phantom_skew_no_residual"
    assert edge["residual_bps"] == 2.0


def test_executor_skips_when_disabled(monkeypatch):
    from backend.services import exchange_technique_executor_service as tex

    monkeypatch.setenv("TECH_EXECUTOR_ENABLED", "0")
    out = tex.execute_techniques_for_opportunity(
        {"symbol": "ADA", "buy_venue": "binance", "sell_venue": "nonkyc", "net_bps": 40},
    )
    assert out.get("skipped") is True
    assert out.get("reason") == "executor_disabled"


def test_executor_gates_phantom_and_applies_size(monkeypatch, tmp_path):
    from backend.services import exchange_technique_executor_service as tex
    from backend.services import exchange_arbitrage_service as arb

    monkeypatch.setenv("TECH_EXECUTOR_ENABLED", "1")
    monkeypatch.setenv("TECH_RESIDUAL_EDGE_BPS", "15")
    monkeypatch.setattr(tex, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(tex, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(tex.ex, "_DATA_DIR", str(tmp_path))

    phantom = tex.execute_techniques_for_opportunity(
        {
            "symbol": "OP",
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "net_bps": 80.0,
            "est_profit_usd": 0.12,
            "notional_usd": 15.0,
            "mid_skew_bps": 78.0,
            "profitable": True,
        },
        mid_skew_bps=78.0,
        force=True,
    )
    assert phantom.get("skip_reason") == "phantom_skew_no_residual"
    assert phantom.get("ready") is False

    monkeypatch.setattr(
        arb,
        "prepare_live_opportunity",
        lambda o, **kw: {
            "ok": True,
            "max_funded_usd": 12.0,
            "requested_usd": 15.0,
            "opportunity": {**o, "notional_usd": 12.0},
        },
    )
    monkeypatch.setattr(
        tex,
        "_apply_technique",
        lambda *a, **k: {"success": True, "skipped": True, "reason": "advisory_only"},
    )
    ready = tex.execute_techniques_for_opportunity(
        {
            "symbol": "ADA",
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "net_bps": 40.0,
            "est_profit_usd": 0.06,
            "notional_usd": 15.0,
            "mid_skew_bps": 10.0,
            "profitable": True,
        },
        mid_skew_bps=10.0,
        force=True,
    )
    assert ready.get("ready") is True
    assert ready.get("success") is True


def test_quote_bridge_raises_on_buy_venue(monkeypatch):
    from backend.services import exchange_courier_arm_service as courier

    monkeypatch.setenv("COURIER_FLOOR_USD", "12")
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.venue_quote_asset",
        lambda v: "USDC" if v == "binance" else "USDT",
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.parse_spot_balances",
        lambda v, **kw: {"USDC": 2.0} if v == "binance" else {"USDT": 20.0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.invalidate_venue_balance_cache",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "backend.services.exchange_spread_hunter_arm_service._raise_quote_on_buy_venue",
        lambda *a, **k: {
            "success": True,
            "action": "prefund_sell",
            "symbol": "ADA",
            "sell_usd": 10.0,
        },
    )
    monkeypatch.setattr(courier, "_append", lambda *a, **k: None)
    out = courier.quote_bridge_for_route(
        {"symbol": "ADA", "buy_venue": "binance", "sell_venue": "nonkyc", "notional_usd": 15},
        need_usd=15.0,
    )
    assert out["success"] is True
    assert out["technique"] == "quote_bridge_rotation"
    assert out["action"]["sell_usd"] == 10.0


def test_latch_recheck_requires_residual(monkeypatch):
    from backend.services import exchange_latch_sniper_service as latch

    monkeypatch.setenv("TECH_RESIDUAL_EDGE_BPS", "15")
    monkeypatch.setenv("LATCH_MIN_BPS", "12")
    monkeypatch.setenv("LATCH_MAX_MID_SKEW_BPS", "200")
    monkeypatch.setattr(
        latch.conn,
        "fetch_ticker",
        lambda venue, sym: {"ask": 1.0, "bid": 0.999} if venue == "binance" else {"ask": 1.01, "bid": 1.009},
    )
    monkeypatch.setattr(latch.conn, "load_connectors_config", lambda: {})
    monkeypatch.setattr(latch.arb, "_effective_transfer_cost_bps", lambda cfg: 6.0)
    monkeypatch.setattr(
        "backend.services.exchange_spread_hunter_arm_service._annotate_opportunity",
        lambda opp, **kw: {
            **opp,
            "net_bps": 30.0,
            "est_profit_usd": 0.04,
            "profitable": True,
            "buy_ask": 1.0,
            "sell_bid": 1.009,
        },
    )
    monkeypatch.setattr(
        "backend.services.exchange_spread_hunter_arm_service.mid_skew_bps",
        lambda *a, **k: 28.0,
    )
    monkeypatch.setattr(
        "backend.services.exchange_spread_hunter_arm_service.regime_deweight_factor",
        lambda **kw: (1.0, None),
    )
    check = latch._recheck_latch({
        "symbol": "ADA",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "notional_usd": 15.0,
    })
    assert check["ok"] is False
    assert check["reason"] == "phantom_skew_no_residual"
