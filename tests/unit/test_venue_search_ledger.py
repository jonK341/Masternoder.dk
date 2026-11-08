"""Ledger rows describe the order body and do not mark it placed."""
import json

from backend.services import venue_search_ledger_service as led


def test_order_spec_names_each_venue_endpoint():
    binance = led.order_spec("binance", "XRP", "buy", 20)
    nonkyc = led.order_spec("nonkyc", "XRP", "sell", 20)
    assert binance["endpoint"] == "POST /api/v3/order"
    assert binance["body"]["symbol"] == "XRPUSDC"
    assert binance["body"]["type"] == "MARKET"
    assert nonkyc["endpoint"] == "POST /api/v2/createorder"
    assert nonkyc["body"]["symbol"] == "XRP_USDT"
    assert nonkyc["body"]["side"] == "sell"


def test_rows_stay_unplaced_when_the_book_is_thin(tmp_path, monkeypatch):
    monkeypatch.setattr(led, "_LEDGER_DIR", str(tmp_path))
    scan = {
        "success": True,
        "tradable_count": 0,
        "coins": [{
            "symbol": "XLM",
            "decision": "book_too_thin",
            "net_bps": 70,
            "executable_usd": 0.2,
            "route": "binance→nonkyc",
            "buy_ask": 0.15,
            "sell_bid": 0.16,
        }],
    }
    rows = led.rows_from_scan(scan, notional_usd=25)
    assert len(rows) == 2
    assert {r["venue"] for r in rows} == {"binance", "nonkyc"}
    assert all(r["placed"] is False for r in rows)
    assert all(r["reason"] == "book_too_thin" for r in rows)
    counts = led.write_rows(rows)
    assert counts == {"binance": 1, "nonkyc": 1}
    saved = json.loads(open(tmp_path / "binance.jsonl", encoding="utf-8").read())
    assert saved["order_body"]["side"] == "BUY"
    assert saved["endpoint"] == "POST /api/v3/order"
