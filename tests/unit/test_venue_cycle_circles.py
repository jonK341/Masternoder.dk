"""Profit preview + daemon gate for venue cycle circles."""
from __future__ import annotations

import os

import pytest

from backend.services import venue_cycle_circles_service as circles


def test_estimate_arb_leg_profitable():
    out = circles.estimate_arb_leg(
        symbol="ALGO",
        direction="binance->nonkyc",
        notional_usd=25.0,
        ask_buy=0.10,
        bid_sell=0.1005,
        fee_buy_bps=10,
        fee_sell_bps=20,
        xfer_bps=0,
    )
    assert out["ok"] is True
    assert out["gross_bps"] == pytest.approx(50.0, abs=0.05)
    assert out["fee_bps"] == pytest.approx(30.0)
    assert out["net_bps"] == pytest.approx(20.0, abs=0.05)
    assert out["profitable"] is True
    assert out["est_profit_usd"] > 0
    assert out["leg_count"] == 3


def test_estimate_arb_leg_unprofitable():
    out = circles.estimate_arb_leg(
        symbol="LINK",
        direction="nonkyc->binance",
        notional_usd=25.0,
        ask_buy=10.0,
        bid_sell=10.01,
        fee_buy_bps=10,
        fee_sell_bps=20,
    )
    assert out["ok"] is True
    assert out["profitable"] is False
    assert out["net_bps"] < 0


def test_estimate_inventory_circle_friction():
    out = circles.estimate_inventory_circle(
        raise_symbol="ADA",
        target_symbol="BNB",
        venue="binance",
        notional_usd=30.0,
        raise_bid=0.17,
        target_ask=650.0,
        fee_sell_bps=10,
        fee_buy_bps=10,
        xfer_bps=0,
    )
    assert out["ok"] is True
    assert out["leg_count"] == 3
    assert out["est_profit_usd"] < 0
    assert out["profitable"] is False


def test_estimate_inventory_circle_four_leg_xfer():
    out = circles.estimate_inventory_circle(
        raise_symbol="ADA",
        target_symbol="XRP",
        venue="binance→nonkyc",
        notional_usd=25.0,
        raise_bid=0.17,
        target_ask=1.02,
        fee_sell_bps=10,
        fee_buy_bps=20,
        xfer_bps=1.0,
    )
    assert out["ok"] is True
    assert out["leg_count"] == 4
    assert any(leg.get("action") == "xfer" for leg in out["legs"])


def test_leg_is_big_profit_gate():
    leg = {
        "profitable": True,
        "fundable": True,
        "net_bps": 16.0,
        "est_profit_usd": 0.08,
    }
    assert circles._leg_is_big_profit(leg, min_net_bps=15.0, min_profit_usd=0.05) is True
    assert circles._leg_is_big_profit(leg, min_net_bps=20.0, min_profit_usd=0.05) is False
    assert circles._leg_is_big_profit(leg, min_net_bps=15.0, min_profit_usd=0.10) is False


def test_dynamic_big_profit_thresholds_scale(monkeypatch):
    monkeypatch.setenv("CYCLE_CIRCLES_MIN_NET_BPS", "15")
    monkeypatch.setenv("CYCLE_CIRCLES_MIN_PROFIT_USD", "0.05")
    bps25, usd25 = circles.dynamic_big_profit_thresholds(25)
    bps50, usd50 = circles.dynamic_big_profit_thresholds(50)
    assert bps25 == 15.0
    assert bps50 <= 10.0
    assert usd50 >= usd25


def test_maybe_auto_cycle_circles_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("CYCLE_CIRCLES_ENABLED", "0")
    monkeypatch.setattr(circles, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(circles, "_LAST_PLAN_PATH", str(tmp_path / "plan.json"))
    out = circles.maybe_auto_cycle_circles(force=True)
    assert out["skipped"] is True
    assert out["reason"] == "circles_disabled"


def test_maybe_auto_cycle_circles_plans_and_skips_small_edge(monkeypatch, tmp_path):
    monkeypatch.setenv("CYCLE_CIRCLES_ENABLED", "1")
    monkeypatch.setenv("CYCLE_CIRCLES_AUTO", "1")
    monkeypatch.setenv("CYCLE_CIRCLES_MIN_NET_BPS", "15")
    monkeypatch.setenv("CYCLE_CIRCLES_MIN_PROFIT_USD", "0.05")
    monkeypatch.setattr(circles, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(circles, "_LAST_PLAN_PATH", str(tmp_path / "plan.json"))

    plan = {
        "planned_at": "now",
        "circle_count": 4,
        "best_net_bps": 8.0,
        "est_arb_profit_usd": 0.02,
        "profitable_arb": [
            {
                "symbol": "LINK",
                "direction": "binance->nonkyc",
                "profitable": True,
                "fundable": True,
                "net_bps": 8.0,
                "est_profit_usd": 0.02,
                "max_funded_usd": 20,
                "ask_buy": 10.0,
                "qty": 2.0,
                "leg_count": 3,
            }
        ],
        "fill_gaps": [],
        "rows": [],
        "quotes": {},
    }

    monkeypatch.setattr(circles, "plan_circles", lambda *a, **k: plan)
    called = {"n": 0}

    def _boom(*a, **k):
        called["n"] += 1
        return {"success": True}

    monkeypatch.setattr(circles, "execute_arb_circle", _boom)
    out = circles.maybe_auto_cycle_circles(force=True)
    assert out["planned"] is True
    assert out["big_profit_count"] == 0
    assert out["skipped_exec"] == "no_big_profit"
    assert called["n"] == 0


def test_maybe_auto_cycle_circles_executes_big_profit(monkeypatch, tmp_path):
    monkeypatch.setenv("CYCLE_CIRCLES_ENABLED", "1")
    monkeypatch.setenv("CYCLE_CIRCLES_AUTO", "1")
    monkeypatch.setenv("CYCLE_CIRCLES_MIN_NET_BPS", "15")
    monkeypatch.setenv("CYCLE_CIRCLES_MIN_PROFIT_USD", "0.05")
    monkeypatch.setenv("CYCLE_CIRCLES_IGNORE_FLOOR", "1")
    monkeypatch.setattr(circles, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(circles, "_LAST_PLAN_PATH", str(tmp_path / "plan.json"))

    plan = {
        "planned_at": "now",
        "circle_count": 4,
        "best_net_bps": 22.0,
        "est_arb_profit_usd": 0.12,
        "profitable_arb": [
            {
                "symbol": "BNB",
                "direction": "binance->nonkyc",
                "profitable": True,
                "fundable": True,
                "net_bps": 22.0,
                "est_profit_usd": 0.12,
                "max_funded_usd": 30,
                "ask_buy": 600.0,
                "qty": 0.04,
                "notional_usd": 25,
                "leg_count": 3,
            }
        ],
        "fill_gaps": [],
        "rows": [],
        "quotes": {},
    }
    monkeypatch.setattr(circles, "plan_circles", lambda *a, **k: plan)

    class _Vapi:
        @staticmethod
        def live_allowed():
            return True

    import sys
    import types

    fake = types.ModuleType("backend.services.exchange_venue_api_service")
    fake.live_allowed = _Vapi.live_allowed
    monkeypatch.setitem(sys.modules, "backend.services.exchange_venue_api_service", fake)

    calls = []

    def _exec(leg, **kwargs):
        calls.append(leg)
        return {"success": True, "symbol": leg.get("symbol"), "direction": leg.get("direction")}

    monkeypatch.setattr(circles, "execute_arb_circle", _exec)
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_event",
        lambda **k: None,
        raising=False,
    )
    out = circles.maybe_auto_cycle_circles(force=True)
    assert out["big_profit_count"] == 1
    assert out.get("executed_count") == 1
    assert calls and calls[0]["symbol"] == "BNB"
