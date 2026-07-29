"""Unit tests for Binance spot reuse (+10% TP / −15% cancel)."""
from __future__ import annotations

import pytest


@pytest.fixture
def spot_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_spot_reuse_service as svc

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    cfg_path = data / "spot_reuse_config.json"
    state_path = data / "spot_reuse_state.json"
    monkeypatch.setattr(svc, "_CFG_PATH", str(cfg_path))
    monkeypatch.setattr(svc, "_STATE_PATH", str(state_path))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setenv("EXCHANGE_SPOT_REUSE_LIVE", "0")
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "0")
    return svc


def test_manage_asset_sets_tp_from_ref(spot_env, monkeypatch):
    svc = spot_env
    row: dict = {}
    placed = []

    def fake_place(venue, asset, side, qty, price, **kw):
        placed.append({"price": price, "qty": qty})
        return {"success": True, "order_id": "paper-1"}

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.place_limit_order",
        fake_place,
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.get_order_status",
        lambda *a, **k: {"success": True, "filled": False, "resting": True},
    )

    res = svc.manage_asset("binance", "DOGE", 1000.0, 0.10, svc.load_config(), row, dry_run=True)
    assert res["action"] == "placed_sell"
    assert res["tp_price"] == pytest.approx(0.11, rel=1e-4)
    assert placed[0]["price"] == pytest.approx(0.11, rel=1e-4)


def test_loss_margin_cancels_and_reseeds(spot_env, monkeypatch):
    svc = spot_env
    row = {"ref_price": 1.0, "sell_order_id": "ord-99", "tp_price": 1.1}
    cancelled = []

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.cancel_order",
        lambda *a, **k: cancelled.append(a) or {"success": True},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.get_order_status",
        lambda *a, **k: {"success": True, "filled": False},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.place_limit_order",
        lambda *a, **k: {"success": True, "order_id": "new-1"},
    )

    res = svc.manage_asset("binance", "BTC", 0.01, 0.84, svc.load_config(), row, dry_run=True)
    assert "loss_cancel" in res["events"]
    assert cancelled
    assert row["ref_price"] == pytest.approx(0.84, rel=1e-6)
