"""Unit tests for the dedicated Binance↔NonKYC dual-farm arm."""
from __future__ import annotations

from backend.services import exchange_dual_farm_arm_service as arm


def test_external_opp_filter():
    assert arm._is_external_opp({"buy_venue": "binance", "sell_venue": "nonkyc"}) is True
    assert arm._is_external_opp({"buy_venue": "binance", "sell_venue": "internal"}) is False
    assert arm._is_external_opp({"buy_venue": "nonkyc", "sell_venue": "nonkyc"}) is False


def test_arm_disabled_skips(monkeypatch):
    monkeypatch.setenv("DUAL_FARM_ARM_ENABLED", "0")
    out = arm.run_dual_farm_arm_tick()
    assert out.get("skipped") is True
    assert out.get("reason") == "arm_disabled"


def test_arm_executes_qualifying_external(monkeypatch, tmp_path):
    monkeypatch.setenv("DUAL_FARM_ARM_ENABLED", "1")
    monkeypatch.setenv("DUAL_FARM_PREFUND", "0")
    monkeypatch.setenv("DUAL_FARM_MIN_BPS", "12")
    monkeypatch.setenv("DUAL_FARM_NOTIONAL_USD", "15")
    monkeypatch.setattr(arm, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(arm.arb, "live_enabled", lambda: False)

    opp = {
        "symbol": "ADA",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "buy_ask": 0.17,
        "sell_bid": 0.175,
        "net_bps": 20.0,
        "est_profit_usd": 0.03,
        "notional_usd": 15.0,
    }
    monkeypatch.setattr(
        arm.arb,
        "scan_opportunities",
        lambda **kw: {"opportunity_count": 2, "opportunities": [
            {**opp, "sell_venue": "internal", "net_bps": 200.0},  # noise
            opp,
        ]},
    )
    monkeypatch.setattr(
        arm.arb,
        "prepare_live_opportunity",
        lambda o, **kw: {"ok": True, "opportunity": dict(o)},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: None,
    )
    calls = {"exec": 0}

    def fake_exec(o, agent_id=None, dry_run=False):
        calls["exec"] += 1
        return {"success": True, "mode": "paper"}

    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.execute_spatial_arbitrage",
        fake_exec,
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.book_agent_profit",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_scan",
        lambda **kw: "path-df-1",
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_execution",
        lambda **kw: None,
    )

    out = arm.run_dual_farm_arm_tick(force=True)
    assert out["executed"] is True
    assert out["external_qualifying"] == 1
    assert out["top"]["symbol"] == "ADA"
    assert calls["exec"] == 1


def test_arm_prefers_prefund_then_retry(monkeypatch, tmp_path):
    monkeypatch.setenv("DUAL_FARM_ARM_ENABLED", "1")
    monkeypatch.setenv("DUAL_FARM_PREFUND", "1")
    monkeypatch.setenv("DUAL_FARM_MIN_BPS", "12")
    monkeypatch.setattr(arm, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(arm.arb, "live_enabled", lambda: True)

    opp = {
        "symbol": "LINK",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "buy_ask": 10.0,
        "sell_bid": 10.05,
        "net_bps": 18.0,
        "est_profit_usd": 0.02,
        "notional_usd": 15.0,
    }
    monkeypatch.setattr(
        arm.arb,
        "scan_opportunities",
        lambda **kw: {"opportunity_count": 1, "opportunities": [opp]},
    )
    prepares = [
        {"ok": False, "reason": "insufficient_venue_balance", "requested_usd": 15.0, "max_funded_usd": 2.0},
        {"ok": True, "opportunity": dict(opp)},
    ]

    def fake_prepare(o, **kw):
        return prepares.pop(0)

    monkeypatch.setattr(arm.arb, "prepare_live_opportunity", fake_prepare)
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        arm,
        "_raise_quote_on_buy_venue",
        lambda *a, **k: {"success": True, "action": "prefund_sell", "symbol": "ADA", "sell_usd": 20.0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.execute_spatial_arbitrage",
        lambda *a, **k: {"success": True, "mode": "live"},
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.book_agent_profit",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_scan",
        lambda **kw: "path-df-2",
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_execution",
        lambda **kw: None,
    )

    out = arm.run_dual_farm_arm_tick(force=True)
    assert out["executed"] is True
    assert out["prefund"]["action"] == "prefund_sell"
    assert out["prefund"]["symbol"] == "ADA"
