from backend.services.exchange_spot_cleanup_service import (
    _drift_bps,
    list_strategy_opens,
    sweep_venue_spots,
)


def test_drift_bps():
    assert _drift_bps(100.0, 100.0) == 0.0
    assert abs((_drift_bps(101.0, 100.0) or 0) - 100.0) < 1e-6


def test_list_and_sweep_dead_dry(monkeypatch):
    import backend.services.exchange_spot_cleanup_service as clean

    monkeypatch.setattr(clean, "_mid", lambda symbol: (1.0, "test"))

    def fake_open(venue, symbol, dry_run=False, quote=None):
        if symbol != "XRP":
            return {"success": True, "body": []}
        return {
            "success": True,
            "body": [
                {"clientOrderId": "ld-XRP-b0n-1", "orderId": "11", "side": "BUY", "price": "0.90", "origQty": "5"},
                {"clientOrderId": "ld-XRP-b1n-2", "orderId": "12", "side": "BUY", "price": "0.999", "origQty": "5"},
                {"clientOrderId": "other-1", "orderId": "99", "side": "BUY", "price": "0.5", "origQty": "1"},
            ],
        }

    monkeypatch.setattr(clean, "get_open_orders", fake_open)
    rows = list_strategy_opens("binance", symbols=["XRP"])
    assert len(rows) == 2
    assert rows[0]["dead"] is True

    cancelled = []

    def fake_cancel(venue, symbol, order_id, dry_run=False, quote=None):
        cancelled.append(order_id)
        return {"success": True}

    monkeypatch.setattr(clean, "cancel_order", fake_cancel)
    monkeypatch.setattr(clean, "invalidate_venue_balance_cache", lambda: None)
    monkeypatch.setattr(clean, "parse_spot_balances", lambda *a, **k: {"USDC": 20.0})

    out = sweep_venue_spots("binance", symbols=["XRP"], min_drift_bps=25.0, dry_run=False)
    assert out["cancelled"] == 1
    assert cancelled == ["11"]

    out_all = sweep_venue_spots("binance", symbols=["XRP"], cancel_all_tagged=True, dry_run=False)
    assert out_all["cancelled"] == 2
