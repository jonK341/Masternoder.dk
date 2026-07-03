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
