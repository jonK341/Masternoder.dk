"""PayPal subscription webhook: idempotency + PAYMENT.SALE.COMPLETED grant."""
from __future__ import annotations

import os

import pytest

from backend.services.monetization_config_service import reload_monetization_config
from backend.services.monetization_subscription_service import (
    process_paypal_webhook_event,
    save_subscription_binding,
)


@pytest.fixture
def isolated_monetization_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path))
    reload_monetization_config()
    yield tmp_path


def test_webhook_duplicate_event_returns_200(isolated_monetization_logs):
    body = {
        "id": "WH-DUP-1",
        "event_type": "PAYMENT.SALE.COMPLETED",
        "resource": {
            "billing_agreement_id": "I-X",
            "state": "COMPLETED",
            "amount": {"total": "1.00", "currency": "USD"},
        },
    }
    save_subscription_binding("I-X", "user_a", "P-PLACEHOLDER-PRO")
    out1, s1 = process_paypal_webhook_event(body)
    out2, s2 = process_paypal_webhook_event(body)
    assert s1 == 200 and out1.get("success")
    assert s2 == 200 and out2.get("duplicate") is True


def test_payment_sale_completed_grants_when_bound(isolated_monetization_logs):
    save_subscription_binding("I-SUB-1", "user_sub_test", "P-PLACEHOLDER-PRO")
    body = {
        "id": "WH-SALE-1",
        "event_type": "PAYMENT.SALE.COMPLETED",
        "resource": {
            "billing_agreement_id": "I-SUB-1",
            "state": "COMPLETED",
            "amount": {"total": "9.99", "currency": "USD"},
        },
    }
    out, status = process_paypal_webhook_event(body)
    assert status == 200
    assert out.get("success")
    assert out.get("handled") == "payment_sale_completed"
    assert out.get("granted") is True
    assert int(out.get("coins_granted") or 0) > 0
