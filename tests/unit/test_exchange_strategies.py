"""The ten daemon strategies: calculations, signals, and log files."""
import json

import pytest


def _rise(n=40, start=1.0, step=0.01, volume=10.0):
    rows = []
    price = start
    for _i in range(n):
        price += step
        rows.append({
            "open": price - step, "high": price + 0.001, "low": price - 0.002,
            "close": price, "volume": volume,
        })
    return rows


def test_two_best_orders_skip_minus_strategies():
    from backend.services.exchange_strategy_service import select_strategy_orders

    scores = {"momentum": 0.694, "news": 0.584, "trend": -1.523, "pairs": -5.939}
    rows = [
        {"strategy": "trend", "symbol": "ALGO", "signal": "long", "ready": True},
        {"strategy": "pairs", "symbol": "XRP/XLM", "signal": "sell", "ready": True},
        {"strategy": "momentum", "symbol": "ALGO", "signal": "flat", "ready": True},
        {"strategy": "news", "symbol": "ALGO", "signal": "long", "ready": True},
        {"strategy": "momentum", "symbol": "XRP", "signal": "long", "ready": True},
    ]
    picked = select_strategy_orders(rows, scores, max_orders=2)
    assert [(row["strategy"], row["symbol"]) for row in picked] == [
        ("momentum", "XRP"),
        ("news", "ALGO"),
    ]


def test_execute_flag_sends_live_signals():
    from backend.services.exchange_strategy_service import load_config

    cfg = load_config()
    assert cfg["execute"] is True
    assert len(cfg["strategies"]) == 10


def test_a_signal_is_sent_once_and_a_flat_pass_sends_nothing(tmp_path):
    from backend.services.exchange_strategy_service import dispatch_strategy_orders

    calls = []

    def place(venue, symbol, side, qty, price, tif):
        calls.append((venue, symbol, side, tif))
        if symbol == "ALGO" and venue == "binance":
            return {"success": False, "error": "Symbol not whitelisted for API key."}
        return {"success": True, "mode": "live", "order_id": f"{venue}-{symbol}"}

    report = {
        "execute": True,
        "max_orders": 10,
        "rows": [
            {"strategy": "trend", "symbol": "ALGO", "signal": "long", "ready": True, "notional_usd": 25},
            {"strategy": "swing", "symbol": "XRP", "signal": "long", "ready": True, "notional_usd": 25},
            {"strategy": "range", "symbol": "XRP", "signal": "sell", "ready": True, "notional_usd": 25},
        ],
    }
    quotes = {
        "ALGO": {"bid": 0.09, "ask": 0.1, "nonkyc_bid": 0.09, "nonkyc_ask": 0.1},
        "XRP": {"bid": 1.16, "ask": 1.17, "nonkyc_bid": 1.15, "nonkyc_ask": 1.16},
    }
    balances = {"binance": {"USDC": 40.0, "XRP": 0.0}, "nonkyc": {"USDT": 12.0, "XRP": 30.0}}
    path = str(tmp_path / "state.json")
    sent = dispatch_strategy_orders(
        report, place=place, balances=balances, quotes=quotes,
        walk_book=lambda _symbol, _usd: 0.1, state_path=path,
    )
    assert ("binance", "XRP", "buy", "IOC") in calls
    assert ("nonkyc", "ALGO", "buy", "GTC") in calls
    assert not any(call[0] == "nonkyc" and call[1] == "XRP" and call[2] == "sell" for call in calls)
    assert any(row.get("order_id") == "binance-XRP" for row in sent)
    again = dispatch_strategy_orders(
        report, place=place, balances=balances, quotes=quotes,
        walk_book=lambda _symbol, _usd: 0.1, state_path=path,
    )
    assert again == []
    assert len(calls) == 3

def test_execute_off_places_nothing(tmp_path):
    from backend.services.exchange_strategy_service import dispatch_strategy_orders

    calls = []
    report = {
        "execute": False,
        "rows": [{"strategy": "swing", "symbol": "XRP", "signal": "long", "ready": True, "notional_usd": 25}],
    }
    sent = dispatch_strategy_orders(
        report,
        place=lambda *args: calls.append(args),
        balances={"binance": {"USDC": 40}, "nonkyc": {}},
        quotes={"XRP": {"bid": 1, "ask": 1.1, "nonkyc_bid": 1, "nonkyc_ask": 1.1}},
        state_path=str(tmp_path / "state.json"),
    )
    assert sent == []
    assert calls == []


def test_all_ten_strategies_are_registered():
    from backend.services.exchange_strategy_service import STRATEGIES

    keys = [key for key, _name in STRATEGIES]
    assert keys == [
        "trend", "momentum", "breakout", "swing", "range",
        "scalp", "reversal", "news", "gap", "pairs",
    ]


def test_trend_and_breakout_go_long_on_a_climb():
    from backend.services.exchange_strategy_service import eval_breakout, eval_swing, eval_trend

    candles = _rise(40)
    candles[-1]["high"] = candles[-1]["close"]
    candles[-1]["close"] = max(row["high"] for row in candles[:-1]) + 0.05
    assert eval_trend("XRP", candles)["signal"] == "long"
    assert eval_breakout("XRP", candles)["signal"] == "long"
    assert eval_swing("XRP", candles)["signal"] == "long"


def test_reversal_buys_a_washed_out_rsi():
    from backend.services.exchange_strategy_service import eval_reversal, rsi

    candles = _rise(20, start=5.0, step=0.0)
    price = 5.0
    for _i in range(16):
        price *= 0.97
        candles.append({"open": price / 0.97, "high": price / 0.97, "low": price, "close": price, "volume": 1})
    value = rsi([row["close"] for row in candles], 14)
    assert value is not None and value < 30
    assert eval_reversal("XRP", candles)["signal"] == "long"


def test_gap_fades_a_jump_and_range_buys_support():
    from backend.services.exchange_strategy_service import eval_gap, eval_range

    daily = [
        {"open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 1},
        {"open": 1.02, "high": 1.03, "low": 1.01, "close": 1.02, "volume": 1},
    ]
    assert eval_gap("XRP", daily)["signal"] == "sell"
    assert eval_gap("XRP", daily)["calc"]["gap_pct"] == pytest.approx(2.0)

    window = []
    for i in range(19):
        window.append({"open": 1.05, "high": 1.10, "low": 1.00, "close": 1.05, "volume": 1})
    window.append({"open": 1.01, "high": 1.02, "low": 1.00, "close": 1.005, "volume": 1})
    row = eval_range("XRP", window)
    assert row["signal"] == "long"
    assert row["calc"]["position"] < 0.15


def test_momentum_needs_return_and_volume():
    from backend.services.exchange_strategy_service import eval_momentum

    candles = []
    for _i in range(20):
        candles.append({"open": 1.0, "high": 1.01, "low": 0.99, "close": 1.0, "volume": 10})
    candles.append({"open": 1.0, "high": 1.03, "low": 1.0, "close": 1.03, "volume": 40})
    row = eval_momentum("XRP", candles)
    assert row["signal"] == "long"
    assert row["calc"]["volume_ratio"] == pytest.approx(4.0)


def test_scalp_waits_for_a_wide_spread_with_size():
    from backend.services.exchange_strategy_service import eval_scalp

    tight = eval_scalp("XRP", bid=1.1614, ask=1.1615, touch_usd=5000, notional_usd=25)
    wide = eval_scalp("XRP", bid=1.00, ask=1.01, touch_usd=40, notional_usd=25)
    assert tight["signal"] == "flat"
    assert tight["calc"]["reason"] == "spread_too_tight"
    assert wide["signal"] == "long"
    assert wide["calc"]["spread_bps"] == pytest.approx(99.5, abs=0.2)


def test_news_and_pairs_flag_a_shock():
    from backend.services.exchange_strategy_service import eval_news, eval_pairs

    quiet = []
    price = 10.0
    for _i in range(25):
        quiet.append({"open": price, "high": price, "low": price, "close": price, "volume": 1})
    shock = list(quiet)
    shock.append({"open": 10.0, "high": 11.0, "low": 10.0, "close": 11.0, "volume": 5})
    assert eval_news("XRP", shock)["signal"] == "long"

    other = []
    price = 10.0
    for _i in range(26):
        other.append({"open": price, "high": price, "low": price, "close": price, "volume": 1})
    row = eval_pairs("XRP", "XLM", shock, other)
    assert row["ready"] is True
    assert row["signal"] in ("long", "sell", "flat")
    assert "z" in row["calc"]


def test_strategy_log_lists_every_strategy(tmp_path):
    from backend.services.exchange_strategy_service import format_strategy_block, run_strategies, write_strategy_logs

    market = {}
    for sym in ("XRP", "XLM"):
        market[sym] = {
            "hourly": _rise(40),
            "daily": _rise(3, step=0.0),
            "bid": 1.0,
            "ask": 1.001,
            "touch_usd": 10,
        }
    report = run_strategies(market, notional_usd=25)
    report["ts"] = "2026-11-08T08:40:00Z"
    report["execute"] = False
    text = format_strategy_block(report)
    for key in ("trend", "momentum", "breakout", "swing", "range", "scalp", "reversal", "news", "gap", "pairs"):
        assert key in text
    paths = write_strategy_logs(report, root=str(tmp_path))
    saved = json.loads((tmp_path / "logs" / "cross_trade" / "strategies_latest.json").read_text(encoding="utf-8"))
    assert paths["ok"] is True
    assert saved["strategies"][0] == "trend"
    assert len(saved["strategies"]) == 10
