"""PayPal order webhook fan-out and outbox tuple unwrap."""
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_webhook_outbox_unwraps_subscription_tuple(tmp_path, monkeypatch):
    """process_paypal_webhook_event returns (dict, status); outbox must not crash on .get."""
    from backend.services import webhook_outbox as wo

    monkeypatch.setattr(wo, "_OUTBOX", str(tmp_path / "outbox.jsonl"))
    monkeypatch.setattr(wo, "_DEAD", str(tmp_path / "dead.jsonl"))

    def _handler(event):
        return ({"success": True, "handled": "payment_sale_completed", "event_id": event.get("id")}, 200)

    with patch(
        "backend.services.monetization_subscription_service.process_paypal_webhook_event",
        side_effect=_handler,
    ):
        out = wo.process_inline(
            "paypal_subscription",
            "WH-TUPLE-1",
            {"event": {"id": "WH-TUPLE-1", "event_type": "PAYMENT.SALE.COMPLETED"}},
            handler="paypal_subscription",
        )
    assert isinstance(out, dict)
    assert out.get("success") is True
    assert out.get("handled") == "payment_sale_completed"


def test_process_paypal_webhook_dispatches_order_capture(tmp_path, monkeypatch):
    """CAPTURE.COMPLETED must reach hosting/onramp/p2p, not be marked ignored."""
    from backend.services.monetization_subscription_service import process_paypal_webhook_event

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path))
    captured = {}

    def _fake_dispatch(event, signature_ok):
        captured["event_type"] = (event or {}).get("event_type")
        captured["signature_ok"] = signature_ok
        return {"success": True, "dispatched": {"hosting": {"success": True}}}

    with patch(
        "backend.services.paypal_order_events.dispatch_order_webhook",
        side_effect=_fake_dispatch,
    ):
        body = {
            "id": "WH-CAP-ORDER-1",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"id": "CAP-1", "custom_id": "mnq_abc"},
        }
        out, status = process_paypal_webhook_event(body)

    assert status == 200
    assert out.get("success") is True
    assert out.get("handled") == "order_event"
    assert captured.get("event_type") == "PAYMENT.CAPTURE.COMPLETED"
    assert captured.get("signature_ok") is True
    assert out.get("ignored") is not True
    assert out.get("duplicate") is not True


def test_dispatch_order_webhook_calls_hosting(monkeypatch):
    from backend.services import paypal_order_events as events

    seen = {}

    monkeypatch.setattr(
        "backend.services.mn2_masternode_hosting_service.handle_webhook",
        lambda ev, signature_ok: seen.setdefault("hosting", {"ok": signature_ok, "type": ev.get("event_type")}),
    )
    monkeypatch.setattr(
        "backend.services.mn2_onramp_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
    )
    monkeypatch.setattr(
        "backend.services.mn2_p2p_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
    )
    monkeypatch.setattr(
        "backend.services.camgirls_paypal_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
    )

    out = events.dispatch_order_webhook(
        {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "PP-1"}},
        True,
    )
    assert out.get("success") is True
    assert seen["hosting"]["ok"] is True
    assert seen["hosting"]["type"] == "CHECKOUT.ORDER.APPROVED"
