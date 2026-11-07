"""Tests for exchange liquidity unlock ops."""
from __future__ import annotations


def test_free_liquidity_dry_run_counts_orders(tmp_path, monkeypatch):
    import backend.services.crypto_exchange_service as ex
    import backend.services.mn2_collateral_liquidity_ops as clo

    orders = [
        {
            "order_id": "a1",
            "user_id": "exchange_agent_casino_liquidity",
            "symbol": "MN2",
            "side": "sell",
            "amount": 100,
            "remaining": 100,
            "quote": "COINS",
            "status": "open",
        }
    ]
    monkeypatch.setattr(ex, "_ORDERS_PATH", str(tmp_path / "orders.json"))
    monkeypatch.setattr(ex, "_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(tmp_path / "wallets"))
    (tmp_path / "wallets").mkdir(parents=True, exist_ok=True)
    ex._write_orders(orders)
    ex._write_json(str(tmp_path / "wallets" / "exchange_agent_casino_liquidity.json"), {"assets": {}})

    snap = clo.liquidity_lock_snapshot()
    assert snap["open_orders"] == 1
    assert snap["locked_mn2_in_orders"] == 100.0

    dry = clo.free_liquidity_from_open_sells(dry_run=True)
    assert dry["would_cancel"] == 1
    assert dry["would_unlock_mn2"] == 100.0
