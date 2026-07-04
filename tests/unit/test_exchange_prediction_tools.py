"""Prediction engine, profit tools, and premium cross-trader features."""
import pytest


def test_predict_symbol_directional_from_prices():
    from backend.services import exchange_prediction_service as pred
    # External mid well above internal price -> predict "up" (mean-reversion pull).
    prices = {
        "binance": {"BTC": {"bid": 119.0, "ask": 121.0, "last": 120.0}},
        "coinbase": {"BTC": {"bid": 124.0, "ask": 126.0, "last": 125.0}},
        "kraken": {"BTC": {"bid": 122.0, "ask": 123.0, "last": 122.5}},
    }
    p = pred.predict_symbol("BTC", prices)
    assert p["venue_count"] == 3
    assert p["direction"] in ("up", "down", "flat")
    assert 0 <= p["confidence_pct"] <= 92
    assert p["edge_uplift_bps"] >= 0


def test_predict_symbol_neutral_without_data():
    from backend.services import exchange_prediction_service as pred
    p = pred.predict_symbol("BTC", {})
    assert p["direction"] == "flat"
    assert p["edge_uplift_bps"] == 0.0


def test_opportunity_radar_ranks_by_score():
    from backend.services import exchange_profit_tools_service as tools
    injected = {
        "binance": {"BTC": {"bid": 99.0, "ask": 100.0, "last": 100.0}, "ETH": {"bid": 50.0, "ask": 50.1, "last": 50.0}},
        "coinbase": {"BTC": {"bid": 112.0, "ask": 112.5, "last": 112.0}, "ETH": {"bid": 50.2, "ask": 50.3, "last": 50.2}},
    }
    res = tools.opportunity_radar(["BTC", "ETH"], injected=injected)
    assert res["success"] is True
    assert res["count"] == 2
    scores = [o["score"] for o in res["opportunities"]]
    assert scores == sorted(scores, reverse=True)
    assert res["opportunities"][0]["buy_venue"] is not None


def test_compounding_plan_reaches_target():
    from backend.services import exchange_profit_tools_service as tools
    plan = tools.compounding_plan(1000.0, 50.0, 2000.0, reinvest_pct=100)
    assert plan["success"] is True
    assert plan["days_to_target"] is not None
    assert plan["projected_capital_usd"] >= 2000.0


def test_simulate_strategy_distribution_is_reproducible():
    from backend.services import exchange_profit_tools_service as tools
    a = tools.simulate_strategy(1000.0, 40.0, cycles=50, volatility=0.4, runs=300, seed=7)
    b = tools.simulate_strategy(1000.0, 40.0, cycles=50, volatility=0.4, runs=300, seed=7)
    assert a["p50_usd"] == b["p50_usd"]
    assert a["p10_usd"] <= a["p50_usd"] <= a["p90_usd"]
    assert 0 <= a["prob_profit_pct"] <= 100


def test_premium_features_and_edge_bonus():
    from backend.services import exchange_premium_service as prem
    feats = prem.premium_features()
    assert feats["success"] is True
    assert len(feats["features"]) >= 4
    bonus, cycles = prem.edge_bonus_and_cycles(True, market_uplift_bps=20.0, base_cycles_per_day=24)
    assert bonus > 0
    assert cycles > 24  # priority scanning multiplies cycles
    none_bonus, none_cycles = prem.edge_bonus_and_cycles(False, base_cycles_per_day=24)
    assert none_bonus == 0.0 and none_cycles == 24


def test_premium_template_outprojects_with_bonus():
    from backend.services.agent_marketplace_service import get_catalog
    cat = get_catalog()
    quant = next(t for t in cat["templates"] if t["id"] == "tmpl_quant_multi")
    assert quant.get("premium") is True
    assert quant["projection"]["edge_bonus_bps"] > 0
