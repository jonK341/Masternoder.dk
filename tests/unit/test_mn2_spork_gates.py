"""Unit tests for exchange/casino spork gate integration."""
from __future__ import annotations

import os

import pytest

from backend.services import mn2_spork_service as spork


@pytest.mark.unit
def test_arbitrage_live_respects_spork(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_112_EXCHANGE_LIVE_TRADING": %d}' % spork.SPORK_OFF,
    )
    spork.invalidate_cache()
    from backend.services import exchange_arbitrage_service as arb

    assert arb.live_enabled() is False


@pytest.mark.unit
def test_arbitrage_live_env_and_spork(monkeypatch):
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    past = int(__import__("time").time()) - 3600
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_112_EXCHANGE_LIVE_TRADING": %d}' % past,
    )
    spork.invalidate_cache()
    from backend.services import exchange_arbitrage_service as arb

    assert arb.live_enabled() is True


@pytest.mark.unit
def test_payout_live_spork_blocks(monkeypatch):
    monkeypatch.setenv("EXCHANGE_PAYOUT_PAYPAL_LIVE", "1")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_114_PAYOUT_LIVE": %d}' % spork.SPORK_OFF,
    )
    spork.invalidate_cache()
    from backend.services import exchange_payout_service as payout

    assert payout._paypal_live_enabled() is False
