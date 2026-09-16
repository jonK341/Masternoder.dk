"""Trader app profit intelligence: recommendations + trade/signal -> profit combination."""
import pytest
from trader_app import intelligence as intel


SIGNALS = [
    {"type": "arbitrage", "symbol": "DOGE", "buy_venue": "binance", "sell_venue": "nonkyc", "net_bps": 22.0, "actionable": True},
    {"type": "arbitrage", "symbol": "ATOM", "buy_venue": "binance", "sell_venue": "internal", "net_bps": 180.0, "actionable": False},
    {"type": "grid", "symbol": "SOL", "venue": "binance", "spread_bps": 10.0, "actionable": True},
    {"type": "grid", "symbol": "XYZ", "venue": "binance", "spread_bps": 4.0, "actionable": True},
]


def test_recommend_ranks_and_labels():
    recs = intel.recommend(SIGNALS, order_size_usd=10.0, cycles_per_day=10)
    syms = [r["symbol"] for r in recs]
    assert "ATOM" not in syms  # not actionable (internal leg)
    doge = next(r for r in recs if r["symbol"] == "DOGE")
    assert doge["recommendation"] == "strong"   # 22 bps
    sol = next(r for r in recs if r["symbol"] == "SOL")
    assert sol["recommendation"] == "consider"  # 10 bps
    xyz = next(r for r in recs if r["symbol"] == "XYZ")
    assert xyz["recommendation"] == "skip"      # 4 bps below floor
    # expected profit math: 10 usd * 22bps = $0.022/cycle * 10 = $0.22/day
    assert doge["expected_per_cycle_usd"] == pytest.approx(0.022)
    assert doge["projected_daily_usd"] == pytest.approx(0.22)
    # ranked by score desc
    assert recs[0]["symbol"] == "DOGE"


def test_recommend_forum_intel_nudges_reason():
    recs = intel.recommend(SIGNALS, order_size_usd=10.0,
                           forum_intel={"DOGE": {"sentiment": 0.5, "mentions": 30}})
    doge = next(r for r in recs if r["symbol"] == "DOGE")
    assert "forum" in doge["reason"]


def test_recommend_has_confidence_monthly_and_risk():
    recs = intel.recommend(SIGNALS, order_size_usd=10.0, cycles_per_day=10)
    doge = next(r for r in recs if r["symbol"] == "DOGE")
    assert 0 <= doge["confidence"] <= 100
    assert doge["projected_monthly_usd"] == pytest.approx(6.6)  # 0.22/day * 30
    assert doge["risk"] == "high"  # nonkyc route -> illiquid/high risk


def test_recommend_dedup_keeps_best_edge():
    sigs = [
        {"type": "arbitrage", "symbol": "DOGE", "buy_venue": "binance", "sell_venue": "nonkyc", "net_bps": 12.0, "actionable": True},
        {"type": "arbitrage", "symbol": "DOGE", "buy_venue": "binance", "sell_venue": "nonkyc", "net_bps": 25.0, "actionable": True},
    ]
    recs = intel.recommend(sigs)
    doge = [r for r in recs if r["symbol"] == "DOGE"]
    assert len(doge) == 1 and doge[0]["edge_bps"] == 25.0


def test_recommend_clamps_bad_inputs():
    recs = intel.recommend(SIGNALS, order_size_usd=-5, cycles_per_day=0)
    # order size clamped to >=1, cycles to >=1 -> positive projections, no crash
    assert all(r["projected_daily_usd"] >= 0 for r in recs)


def test_combine_profit_merges_realized_and_projected():
    grid_state = {"BINANCE:DOGE": {"realized_pnl_usd": 1.84}, "NONKYC:LTC": {"realized_pnl_usd": -0.31}}
    pm = intel.combine_profit(SIGNALS, grid_state, order_size_usd=10.0, cycles_per_day=10)
    assert pm["realized_pnl_usd"] == pytest.approx(1.53)
    # projected excludes 'skip' (XYZ); DOGE 0.22 + SOL 0.10 = 0.32
    assert pm["projected_daily_usd"] == pytest.approx(0.32)
    assert pm["projected_monthly_usd"] == pytest.approx(9.6)
    assert pm["actionable_count"] == 2
    assert pm["sources"][0]["source"] == "arbitrage:DOGE"


def test_ai_summary_heuristic():
    pm = intel.combine_profit(SIGNALS, {"BINANCE:DOGE": {"realized_pnl_usd": 1.0}})
    recs = intel.recommend(SIGNALS)
    out = intel.ai_summary(pm, recs)
    assert out["source"] == "heuristic"
    assert "Realized" in out["summary"]
