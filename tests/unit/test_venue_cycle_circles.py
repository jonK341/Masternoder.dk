"""Profit preview math for venue_cycle_circles."""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "scripts", "venue_cycle_circles.py")


def _load():
    spec = importlib.util.spec_from_file_location("venue_cycle_circles", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["venue_cycle_circles"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_estimate_arb_leg_profitable():
    mod = _load()
    # 50 bps gross, 30 bps fees -> +20 bps net
    out = mod.estimate_arb_leg(
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
    assert len(out["legs"]) == 3


def test_estimate_arb_leg_unprofitable():
    mod = _load()
    out = mod.estimate_arb_leg(
        symbol="LINK",
        direction="nonkyc->binance",
        notional_usd=25.0,
        ask_buy=10.0,
        bid_sell=10.01,  # 10 bps gross < 30 fee
        fee_buy_bps=10,
        fee_sell_bps=20,
    )
    assert out["ok"] is True
    assert out["profitable"] is False
    assert out["net_bps"] < 0


def test_estimate_inventory_circle_friction():
    mod = _load()
    out = mod.estimate_inventory_circle(
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
    assert out["est_profit_usd"] < 0  # fees only → friction
    assert out["profitable"] is False


def test_estimate_inventory_circle_four_leg_xfer():
    mod = _load()
    out = mod.estimate_inventory_circle(
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
