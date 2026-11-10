"""Daemon-owned ladder+maker book loop helpers."""
from scripts import all_profit_daemons as apd


def test_summarize_book_includes_venues():
    summary = apd._summarize_book({
        "maker": {"execute": True, "open": 2},
        "ladders": {
            "nonkyc": {"open": 18, "realized_usd": 0.0},
            "binance": {"open": 15, "realized_usd": 0.67},
        },
    })
    assert "maker_exec=True" in summary
    assert "maker_open=2" in summary
    assert "nonkyc_open=18" in summary
    assert "binance_open=15" in summary
    assert "binance_pnl=$0.67" in summary


def test_summarize_book_reads_open_orders_and_yield_flag():
    summary = apd._summarize_book({
        "maker": {"execute": True, "yielded_to_ladder": True, "quotes": [
            {"symbol": "XRP", "side": "sell", "success": True, "coid": "mk-1"},
            {"symbol": "XLM", "side": "sell", "skipped": "inventory"},
        ]},
        "ladders": {
            "binance": {"open_orders": 5, "realized_usd": 0.77},
            "nonkyc": {"open_orders": 20, "realized_usd": 0.02},
        },
    })
    assert "maker_open=1" in summary
    assert "maker_buys=yielded" in summary
    assert "binance_open=5" in summary
    assert "nonkyc_open=20" in summary


def test_book_once_sets_ownership(monkeypatch):
    monkeypatch.delenv("EXCHANGE_DAEMON_OWNS_BOOK", raising=False)

    def fake_maker():
        return {"execute": True, "open": 1, "quotes": []}

    def fake_ladder(venue=None):
        return {"execute": True, "open": 3, "venue": venue, "realized_usd": 0.1}

    monkeypatch.setattr(
        "backend.services.exchange_maker_quote_service.run_maker_quotes",
        fake_maker,
    )
    monkeypatch.setattr(
        "backend.services.exchange_maker_quote_service.write_maker_log",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "backend.services.exchange_ladder_service.run_ladder",
        fake_ladder,
    )
    monkeypatch.setattr(
        "backend.services.exchange_ladder_service.write_ladder_log",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "backend.services.exchange_registry_service.ladder_venues",
        lambda: ("nonkyc", "binance"),
    )

    out = apd._book_once()
    assert out["owned_by"] == "all_profit_daemons"
    assert out["maker"]["open"] == 1
    assert set(out["ladders"]) == {"nonkyc", "binance"}
    assert os_environ_owns_book()


def os_environ_owns_book() -> bool:
    import os

    return str(os.environ.get("EXCHANGE_DAEMON_OWNS_BOOK", "")).strip() in ("1", "true", "yes", "on")
