"""Film monitor free program + optional paid mode."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


@pytest.fixture
def billing(tmp_path, monkeypatch):
    path = tmp_path / "film_monitor_billing.json"
    monkeypatch.setattr(
        "backend.services.film_monitor_billing_service._DATA_FILE",
        str(path),
    )
    monkeypatch.delenv("FILM_MONITOR_PROMO_STARTED_AT", raising=False)
    monkeypatch.delenv("FILM_MONITOR_ALWAYS_FREE", raising=False)
    from backend.services import film_monitor_billing_service as mod

    return mod


def test_free_program_allows_play(billing, monkeypatch):
    monkeypatch.setenv("FILM_MONITOR_ALWAYS_FREE", "1")
    status = billing.get_status("alice", start_trial=True)
    assert status["success"] is True
    assert status["always_free"] is True
    assert status["free_program"] is True
    assert status["can_play"] is True
    assert status["pay_options"] == {}

    access = billing.assert_can_play("alice")
    assert access["can_play"] is True
    assert access["reason"] == "free_program"


def test_paid_mode_after_free_window_requires_payment_or_credit(billing, monkeypatch):
    monkeypatch.setenv("FILM_MONITOR_ALWAYS_FREE", "0")
    started = datetime.now(timezone.utc) - timedelta(hours=25)
    monkeypatch.setenv("FILM_MONITOR_PROMO_STARTED_AT", started.isoformat().replace("+00:00", "Z"))

    blocked = billing.assert_can_play("bob")
    assert blocked["can_play"] is False
    assert blocked["code"] == "PAYMENT_REQUIRED"
    assert "mn2" in blocked["pay_options"]
    assert "paypal" in blocked["pay_options"]

    grant = billing.grant_credit("bob", credits=1, source="test")
    assert grant["credits"] == 1
    access = billing.assert_can_play("bob", consume_credit=True)
    assert access["can_play"] is True
    assert access["reason"] == "credit"
    assert access["credits"] == 0

    blocked_again = billing.assert_can_play("bob")
    assert blocked_again["can_play"] is False


def test_paypal_fulfillment_grants_credit(billing, monkeypatch):
    monkeypatch.setenv("FILM_MONITOR_ALWAYS_FREE", "0")
    started = datetime.now(timezone.utc) - timedelta(hours=30)
    monkeypatch.setenv("FILM_MONITOR_PROMO_STARTED_AT", started.isoformat().replace("+00:00", "Z"))
    out = billing.fulfill_paypal_purchase("carol", "ORDER123", amount=1.99)
    assert out["success"] is True
    assert out["item_granted"] == billing.ITEM_ID
    status = billing.get_status("carol")
    assert status["credits"] == 1
    assert billing.is_film_monitor_item("film-monitor-play")
