"""Venue API pair resolution — resolve_market, venue_supports_symbol, market_order_for_leg."""
import pytest


def test_resolve_market_binance_usdc():
    from backend.services import exchange_venue_api_service as vapi

    out = vapi.resolve_market("binance", "BTC", "USDC")
    assert out["ok"] is True
    assert out["base"] == "BTC"
    assert out["quote"] == "USDC"
    assert out["market"] == "BTCUSDC"


def test_resolve_market_nonkyc_usdt():
    from backend.services import exchange_venue_api_service as vapi

    out = vapi.resolve_market("nonkyc", "DOGE", "USDT")
    assert out["ok"] is True
    assert out["base"] == "DOGE"
    assert out["quote"] == "USDT"
    assert out["market"] == "DOGE_USDT"


def test_resolve_market_unknown_venue():
    from backend.services import exchange_venue_api_service as vapi

    out = vapi.resolve_market("not_a_venue", "BTC")
    assert out["ok"] is False
    assert out["error"] == "unknown_venue"


def test_venue_supports_symbol_with_ticker(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.conn.fetch_ticker",
        lambda vid, sym, timeout=6.0: {"bid": 1.0, "ask": 1.01, "last": 1.0},
    )
    assert vapi.venue_supports_symbol("nonkyc", "DOGE") is True


def test_venue_supports_symbol_unsupported(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.conn.fetch_ticker",
        lambda vid, sym, timeout=6.0: None,
    )
    assert vapi.venue_supports_symbol("bitstamp", "DOGE") is False


def test_market_order_for_leg_buy(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    monkeypatch.setattr(vapi, "venue_supports_symbol", lambda vid, sym, quote=None: True)
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.conn.fetch_ticker",
        lambda vid, sym, timeout=6.0: {"bid": 0.14, "ask": 0.15, "last": 0.15},
    )
    monkeypatch.setattr(
        vapi,
        "normalize_order_qty",
        lambda *a, **k: {"ok": True, "quantity": 200.0, "notional_usd": 30.0, "adjusted": False},
    )
    spec = vapi.market_order_for_leg("nonkyc", "buy", "DOGE", 30.0)
    assert spec["ok"] is True
    assert spec["side"] == "buy"
    assert spec["market"] == "DOGE_USDT"
    assert spec["quantity"] > 0


def test_market_order_for_leg_unsupported_pair(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    monkeypatch.setattr(vapi, "venue_supports_symbol", lambda vid, sym, quote=None: False)
    spec = vapi.market_order_for_leg("bitstamp", "buy", "DOGE", 25.0)
    assert spec["ok"] is False
    assert "pair_not_supported:DOGE" in spec["error"]


def test_normalize_order_qty_binance_lot_size(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    monkeypatch.setattr(
        vapi,
        "fetch_binance_symbol_filters",
        lambda market, force_refresh=False: {
            "ok": True,
            "market": "LINKUSDC",
            "step_size": 0.01,
            "min_qty": 0.01,
            "max_qty": 9000000.0,
            "min_notional": 5.0,
        },
    )
    out = vapi.normalize_order_qty("binance", "LINK", "buy", 10.63829787, price=7.82, market="LINKUSDC")
    assert out["ok"] is True
    assert out["quantity"] == 10.63
    assert out["adjusted"] is True
    assert out["notional_usd"] >= 5.0


def test_normalize_order_qty_bumps_to_min_notional(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    monkeypatch.setattr(
        vapi,
        "fetch_binance_symbol_filters",
        lambda market, force_refresh=False: {
            "ok": True,
            "market": "BTCUSDC",
            "step_size": 0.00001,
            "min_qty": 0.00001,
            "max_qty": 9000.0,
            "min_notional": 10.0,
        },
    )
    out = vapi.normalize_order_qty("binance", "BTC", "buy", 0.00001, price=50000.0, market="BTCUSDC")
    assert out["ok"] is True
    assert out["quantity"] == 0.0002
    assert out["notional_usd"] >= 10.0


def test_normalize_order_qty_below_min_notional_when_capped(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    monkeypatch.setattr(
        vapi,
        "fetch_binance_symbol_filters",
        lambda market, force_refresh=False: {
            "ok": True,
            "market": "BTCUSDC",
            "step_size": 0.00001,
            "min_qty": 0.00001,
            "max_qty": 0.00005,
            "min_notional": 10.0,
        },
    )
    out = vapi.normalize_order_qty("binance", "BTC", "buy", 0.00001, price=50000.0, market="BTCUSDC")
    assert out["ok"] is False
    assert out["error"] == "below_min_notional"


def test_place_market_order_applies_binance_filters(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    captured = {}

    def fake_request(venue_id, endpoint_key, params, dry_run=None, rotation=False):
        captured["quantity"] = params.get("quantity")
        return {"success": True, "body": {"orderId": 1}}

    monkeypatch.setattr(vapi, "normalize_order_qty", lambda *a, **k: {
        "ok": True, "quantity": 10.63, "adjusted": True,
    })
    monkeypatch.setattr(vapi, "venue_api_request", fake_request)
    monkeypatch.setattr(vapi, "live_gate_ok", lambda rotation=False: True)
    monkeypatch.setattr(vapi, "venue_has_credentials", lambda vid: True)

    res = vapi.place_market_order("binance", "LINK", "buy", 10.63829787, dry_run=False)
    assert res["success"] is True
    assert captured["quantity"] == 10.63


def test_balance_cache_refresh_and_age(monkeypatch):
    from backend.services import exchange_venue_api_service as vapi

    vapi.invalidate_venue_balance_cache()
    calls = {"n": 0}

    def fake_balance(venue_id, asset="", *, dry_run=None):
        calls["n"] += 1
        return {"success": True, "body": {"balances": [{"asset": "USDT", "free": "25.79"}]}}

    monkeypatch.setattr(vapi, "venue_has_credentials", lambda vid: vid == "nonkyc")
    monkeypatch.setattr(vapi, "get_account_balance", fake_balance)

    first = vapi.parse_spot_balances("nonkyc", dry_run=False)
    assert first.get("USDT") == 25.79
    assert calls["n"] == 1

    second = vapi.parse_spot_balances("nonkyc", dry_run=False)
    assert second.get("USDT") == 25.79
    assert calls["n"] == 1

    vapi.refresh_venue_balances(["nonkyc"], force=True)
    assert calls["n"] == 2
    assert vapi.balance_cache_age_sec("nonkyc") is not None

