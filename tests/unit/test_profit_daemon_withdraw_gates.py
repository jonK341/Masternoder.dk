from backend.services.profit_daemon_ops_service import (
    cap_notional_to_book_depth,
    check_slippage_guard,
    evaluate_chain_rebalance,
    opportunity_latency_buffer_pct,
)


def test_evaluate_chain_rebalance_blocks_small_moves():
    gate = evaluate_chain_rebalance(move_usd=50.0, fee_usd=1.5)
    assert gate["allowed"] is False
    assert gate["broadcast"] is False
    assert gate["fee_bps"] == 300.0
    assert "fee_bps_too_high" in gate["reasons"]
    ok = evaluate_chain_rebalance(move_usd=600.0, fee_usd=1.5, premium_open_sec=900)
    assert ok["allowed"] is True
    assert ok["fee_bps"] <= 30.0


def test_slippage_guard_enforces_known_depth():
    opp = {"symbol": "XRP", "buy_ask": 1.1, "sell_bid": 1.12, "buy_depth_usd": 40, "sell_depth_usd": 40}
    assert check_slippage_guard(opp, notional_usd=10)["ok"] is True
    assert check_slippage_guard(opp, notional_usd=30)["ok"] is False


def test_cap_notional_to_book_depth():
    out = cap_notional_to_book_depth({"buy_depth_usd": 40, "sell_depth_usd": 50}, 100)
    assert out["capped"] is True
    assert out["notional_usd"] == 20.0


def test_latency_buffer_picks_slower_leg():
    assert opportunity_latency_buffer_pct({"buy_venue": "binance", "sell_venue": "nonkyc"}) == 0.04
