"""Plain-language lines for the fast USDT desk."""
from backend.services.fast_desk_service import describe_coin, summarize_tick


def test_thin_book_says_how_much_is_there():
    text = describe_coin({
        "symbol": "XLM",
        "decision": "book_too_thin",
        "net_bps": 71.8,
        "executable_usd": 0.29,
    })
    assert "XLM" in text
    assert "71.8 bps" in text
    assert "$0.29" in text
    assert "Waiting" in text


def test_inside_fees_waits():
    text = describe_coin({"symbol": "XRP", "decision": "below_fees", "net_bps": -56.0, "executable_usd": 0})
    assert text.startswith("XRP:")
    assert "inside the fees" in text


def test_summary_names_a_ready_coin():
    text = summarize_tick([
        {"symbol": "XRP", "decision": "below_fees", "net_bps": -10, "executable_usd": 0},
        {"symbol": "SOL", "decision": "paper_candidate", "net_bps": 40, "executable_usd": 30},
    ])
    assert text.startswith("Paper fill ready for SOL.")
    assert "XRP:" in text


def test_interesting_stats_kpis(monkeypatch, tmp_path):
    from backend.services import fast_desk_service as desk

    monkeypatch.setattr(desk, "_ladder_venue_stats", lambda venue: {
        "venue": venue, "open": 3 if venue == "nonkyc" else 1, "buys": 2, "sells": 1,
        "pending_exits": 0, "realized_usd": 0.4 if venue == "nonkyc" else 0.1, "symbols": {"DOGE": 3},
    })
    monkeypatch.setattr(desk, "_maker_stats", lambda: {"venue": "binance", "open": 2, "quotes": [], "execute": True})
    monkeypatch.setattr(desk, "_daemon_stats", lambda: {"zero_fill_streak": 4, "loops": {}})
    monkeypatch.setattr(desk, "_threshold_stats", lambda: {"ready": True, "best_net_bps": 22.0, "top_symbol": "SOL"})
    monkeypatch.setattr(desk, "_fill_model_stats", lambda: {"status": "trained", "n": 40})
    monkeypatch.setattr(desk, "_desk_maint_stats", lambda: {})

    state = {
        "coins": [
            {"symbol": "SOL", "decision": "paper_candidate", "net_bps": 40, "executable_usd": 30, "route": "n->b"},
            {"symbol": "XRP", "decision": "below_fees", "net_bps": -5, "executable_usd": 0},
        ],
        "lines": [{"ts": "t", "tradable_count": 1}, {"ts": "t2", "tradable_count": 0}],
    }
    stats = desk.interesting_stats(state)
    assert stats["kpis"]["ready"] == 1
    assert stats["kpis"]["best_net_bps"] == 40
    assert stats["kpis"]["ladder_open"] == 4
    assert stats["kpis"]["ladder_realized_usd"] == 0.5
    assert stats["kpis"]["maker_open"] == 2
    assert stats["gap"]["fee_blocked"] == 1
    monkeypatch.setattr(desk, "_read_state", lambda: state)
    monkeypatch.setattr(desk, "desk_live_status", lambda: ("live", True))
    out = desk.snapshot()
    assert "stats" in out and out["stats"]["kpis"]["ready"] == 1
    assert out["mode"] == "live"
    assert out["live_orders"] is True


def test_desk_live_status_follows_arb_gate(monkeypatch):
    from backend.services import fast_desk_service as desk

    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    monkeypatch.delenv("EXCHANGE_CROSS_TRADE_LIVE", raising=False)
    monkeypatch.delenv("EXCHANGE_DAEMON_MODE", raising=False)
    monkeypatch.setattr(desk, "_daemon_stats", lambda: {})
    mode, live = desk.desk_live_status()
    assert mode == "live"
    assert live is True


def test_summary_uses_live_wording():
    text = summarize_tick(
        [{"symbol": "SOL", "decision": "paper_candidate", "net_bps": 40, "executable_usd": 30}],
        live=True,
    )
    assert text.startswith("Live fill ready for SOL.")
