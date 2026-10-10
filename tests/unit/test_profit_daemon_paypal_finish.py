"""Profit daemon PayPal auto-capture tick."""
from __future__ import annotations


def test_paypal_finish_disabled(monkeypatch):
    from backend.services.profit_daemon_paypal_finish_service import run_paypal_finish_tick

    monkeypatch.setenv("PROFIT_DAEMON_PAYPAL_FINISH", "0")
    out = run_paypal_finish_tick()
    assert out.get("skipped") is True


def test_paypal_finish_tick_calls_sweeper(monkeypatch):
    from backend.services import profit_daemon_paypal_finish_service as svc

    monkeypatch.setenv("PROFIT_DAEMON_PAYPAL_FINISH", "1")
    monkeypatch.setenv("PROFIT_DAEMON_PAYPAL_FINISH_LIMIT", "3")

    def _fake_finish(**_kwargs):
        return {
            "success": True,
            "counts": {
                "pending_found": 2,
                "captured": 1,
                "awaiting_payer": 1,
                "expired": 0,
                "failed": 0,
                "skipped": 0,
            },
            "results": [],
        }

    monkeypatch.setattr(
        "backend.services.paypal_order_events.finish_pending_paypal_orders",
        _fake_finish,
    )
    out = svc.run_paypal_finish_tick()
    assert out.get("success") is True
    assert "captured=1" in out.get("summary", "")
