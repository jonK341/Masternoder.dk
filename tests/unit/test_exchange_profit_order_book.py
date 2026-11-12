"""Unit tests for profit order book + leg techniques."""
from __future__ import annotations

from backend.services import exchange_profit_order_book_service as book


def test_ten_techniques_catalog():
    assert len(book.LEG_TECHNIQUES) == 10
    ids = {t["id"] for t in book.LEG_TECHNIQUES}
    assert "prefund_buy_quote" in ids
    assert "orphan_leg_hedge" in ids
    assert "profit_floor_kill" in ids


def test_score_techniques_recommends_prefund_when_unfunded():
    opp = {
        "symbol": "OP",
        "buy_venue": "nonkyc",
        "sell_venue": "binance",
        "net_bps": 40.0,
        "est_profit_usd": 0.06,
        "notional_usd": 15.0,
    }
    funding = {"ok": False, "reason": "insufficient_venue_balance", "max_funded_usd": 2.0}
    scored = book.score_techniques_for_deal(
        opp, funding=funding, state={}, min_bps=12.0, min_profit=0.02,
    )
    assert scored[0]["id"] in {"profit_floor_kill", "recheck_regime_deweight", "prefund_buy_quote", "size_to_funded", "stale_route_cooldown"}
    pref = next(t for t in scored if t["id"] == "prefund_buy_quote")
    assert pref["recommend"] is True


def test_score_techniques_floor_kill_when_edge_gone():
    opp = {"symbol": "ADA", "buy_venue": "binance", "sell_venue": "nonkyc", "net_bps": 2.0, "est_profit_usd": 0.001, "notional_usd": 15}
    scored = book.score_techniques_for_deal(
        opp, funding={"ok": True}, state={}, min_bps=12.0, min_profit=0.02,
    )
    kill = next(t for t in scored if t["id"] == "profit_floor_kill")
    assert kill["recommend"] is True


def test_book_disabled_skips(monkeypatch):
    monkeypatch.setenv("PROFIT_BOOK_ENABLED", "0")
    out = book.run_profit_order_book_tick()
    assert out.get("skipped") is True


def test_build_order_book_top5(monkeypatch, tmp_path):
    monkeypatch.setenv("PROFIT_BOOK_ENABLED", "1")
    monkeypatch.setenv("PROFIT_BOOK_TOP_N", "5")
    monkeypatch.setenv("PROFIT_BOOK_MIN_BPS", "12")
    monkeypatch.setenv("PROFIT_BOOK_MIN_PROFIT_USD", "0.01")
    monkeypatch.setattr(book, "_BOOK_PATH", str(tmp_path / "book.json"))
    monkeypatch.setattr(book, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(book, "_STATE_PATH", str(tmp_path / "state.json"))

    deals = []
    for i, sym in enumerate(["OP", "RENDER", "POL", "CRV", "LINK", "ADA"]):
        deals.append({
            "symbol": sym,
            "buy_venue": "nonkyc",
            "sell_venue": "binance",
            "buy_ask": 1.0,
            "sell_bid": 1.05 - i * 0.001,
            "gross_bps": 500 - i * 10,
            "fee_bps": 36,
            "net_bps": 80 - i * 5,
            "est_profit_usd": 0.12 - i * 0.01,
            "notional_usd": 15.0,
            "profitable": True,
        })
    monkeypatch.setattr(
        book,
        "_scan_deals",
        lambda **kw: {"symbols": [d["symbol"] for d in deals], "universe": {}, "deals": deals, "xfer_bps": 6, "cfg": {}},
    )
    monkeypatch.setattr(
        book,
        "_funding_snapshot",
        lambda opp, **kw: {"ok": False, "reason": "insufficient_venue_balance", "max_funded_usd": 3.0, "opportunity": opp},
    )

    built = book.build_order_book()
    assert built["deal_count"] == 6
    assert len(built["top5"]) == 5
    assert built["top5"][0]["symbol"] == "OP"
    assert built["top5"][0]["best_technique"]
    assert len(built["techniques_catalog"]) == 10
    assert built["buy_side"][0]["action"].startswith("BUY")
    assert built["sell_side"][0]["action"].startswith("SELL")
    # ledger written
    tail = book._tail_ledger(10)
    assert any(r.get("kind") == "hit" for r in tail)

    tick = book.run_profit_order_book_tick(force=True, apply=False)
    assert tick["success"] is True
    assert tick["best"]["symbol"] == "OP"
