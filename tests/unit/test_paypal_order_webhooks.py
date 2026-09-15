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
    monkeypatch.setattr(
        "backend.services.crypto_exchange_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
    )
    monkeypatch.setattr(
        "backend.services.exchange_user_controller_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
    )
    monkeypatch.setattr(
        "backend.services.casino_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
    )

    out = events.dispatch_order_webhook(
        {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "PP-1"}},
        True,
    )
    assert out.get("success") is True
    assert seen["hosting"]["ok"] is True
    assert seen["hosting"]["type"] == "CHECKOUT.ORDER.APPROVED"


def test_dispatch_order_webhook_calls_exchange(monkeypatch):
    from backend.services import paypal_order_events as events

    seen = {}
    monkeypatch.setattr(
        "backend.services.mn2_masternode_hosting_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
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
    monkeypatch.setattr(
        "backend.services.crypto_exchange_service.handle_webhook",
        lambda ev, signature_ok: seen.setdefault("exchange", {"ok": signature_ok, "type": ev.get("event_type")}),
    )
    monkeypatch.setattr(
        "backend.services.exchange_user_controller_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
    )
    monkeypatch.setattr(
        "backend.services.casino_service.handle_webhook",
        lambda ev, signature_ok: {"success": True, "ignored": True},
    )
    out = events.dispatch_order_webhook(
        {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "PP-EX"}},
        True,
    )
    assert out.get("success") is True
    assert seen["exchange"]["ok"] is True
    assert seen["exchange"]["type"] == "CHECKOUT.ORDER.APPROVED"


def test_collect_pending_keeps_exchange_ahead_of_shop_copy(tmp_path, monkeypatch):
    from backend.services import paypal_order_events as events
    from backend.services import paypal_service as svc

    monkeypatch.setattr(svc, "_SHOP_ORDERS_PATH", str(tmp_path / "paypal_shop_orders.json"))
    svc.remember_shop_order("PAY-EX-1", {
        "status": "pending",
        "item_id": "mn2-starter",
        "user_id": "shop_copy_user",
        "metadata": {"source": "exchange", "item_id": "mn2-starter", "user_id": "shop_copy_user"},
    })
    monkeypatch.setattr(
        "backend.services.crypto_exchange_service.list_pending_paypal_payments",
        lambda: [{
            "rail": "exchange_mn2",
            "local_id": "PAY-EX-1",
            "paypal_order_id": "PAY-EX-1",
            "user_id": "real_exchange_buyer",
            "item_id": "mn2-starter",
        }],
    )
    for spec in (
        "backend.services.mn2_masternode_hosting_service.list_pending_paypal_payments",
        "backend.services.mn2_onramp_service.list_pending_paypal_payments",
        "backend.services.mn2_p2p_service.list_pending_paypal_payments",
        "backend.services.camgirls_paypal_service.list_pending_paypal_payments",
        "backend.services.casino_service.list_pending_paypal_deposits",
        "backend.services.exchange_user_controller_service.list_pending_paypal_payments",
    ):
        monkeypatch.setattr(spec, lambda: [])

    jobs = events.collect_pending_paypal_jobs()
    assert len(jobs) == 1
    assert jobs[0]["rail"] == "exchange_mn2"
    assert jobs[0]["user_id"] == "real_exchange_buyer"


def test_extra_order_ids_default_to_shop_and_classify_crypto(tmp_path, monkeypatch):
    from backend.services import paypal_order_events as events
    from backend.services import paypal_service as svc

    monkeypatch.setattr(svc, "_SHOP_ORDERS_PATH", str(tmp_path / "paypal_shop_orders.json"))
    svc.remember_shop_order("PAY-CRYPTO-EXTRA", {
        "status": "pending",
        "item_id": "crypto:USDC",
        "user_id": "crypto_buyer",
        "metadata": {"source": "exchange_crypto", "user_id": "crypto_buyer"},
    })
    for spec in (
        "backend.services.mn2_masternode_hosting_service.list_pending_paypal_payments",
        "backend.services.mn2_onramp_service.list_pending_paypal_payments",
        "backend.services.mn2_p2p_service.list_pending_paypal_payments",
        "backend.services.camgirls_paypal_service.list_pending_paypal_payments",
        "backend.services.casino_service.list_pending_paypal_deposits",
        "backend.services.crypto_exchange_service.list_pending_paypal_payments",
        "backend.services.exchange_user_controller_service.list_pending_paypal_payments",
    ):
        monkeypatch.setattr(spec, lambda: [])

    jobs = events.collect_pending_paypal_jobs(["PAY-CRYPTO-EXTRA", "PAY-SHOP-DASHBOARD"])
    by_id = {j["paypal_order_id"]: j for j in jobs}
    assert by_id["PAY-CRYPTO-EXTRA"]["rail"] == "exchange_crypto"
    assert by_id["PAY-SHOP-DASHBOARD"]["rail"] == "shop"


def test_rail_from_shop_row_keeps_non_shop_checkouts_off_shop_fulfillment():
    from backend.services.paypal_order_events import _rail_from_shop_row

    assert _rail_from_shop_row({"item_id": "boost-a"}) == "shop"
    assert _rail_from_shop_row({"metadata": {"product": "camgirls"}, "item_id": "camgirls_unlock"}) == "camgirls"
    assert _rail_from_shop_row({"metadata": {"casino_deposit": True}}) == "casino"
    assert _rail_from_shop_row({"metadata": {"source": "exchange_crypto"}, "item_id": "crypto:BTC"}) == "exchange_crypto"


def test_paypal_buyer_id_uses_pending_when_default_user():
    from backend.services.crypto_exchange_service import paypal_buyer_id

    uid, err = paypal_buyer_id("default_user", "real_buyer")
    assert uid == "real_buyer"
    assert err == ""
    uid, err = paypal_buyer_id("alice", "bob")
    assert uid == ""
    assert err == "user_mismatch"
