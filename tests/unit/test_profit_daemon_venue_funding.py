"""Dual-venue prefund tick from profit daemon."""
from __future__ import annotations


def test_venue_prefund_skipped_when_disabled(monkeypatch):
    from backend.services.profit_daemon_venue_funding_service import maybe_ensure_dual_venue_funding

    monkeypatch.setenv("PROFIT_DAEMON_VENUE_PREFUND", "0")
    out = maybe_ensure_dual_venue_funding({"platform": {}})
    assert out.get("skipped") is True


def test_dispatch_order_webhook_immediate_capture_on_approved(monkeypatch):
    from backend.services import paypal_order_events as events

    captured = []

    monkeypatch.setattr(
        "backend.services.paypal_service.finish_checkout_order",
        lambda oid: captured.append(oid) or {"success": True, "order_id": oid},
    )
    for mod in (
        "backend.services.mn2_masternode_hosting_service",
        "backend.services.mn2_onramp_service",
        "backend.services.mn2_p2p_service",
        "backend.services.camgirls_paypal_service",
        "backend.services.crypto_exchange_service",
        "backend.services.exchange_user_controller_service",
        "backend.services.casino_service",
    ):
        monkeypatch.setattr(
            f"{mod}.handle_webhook",
            lambda ev, signature_ok: {"success": True, "ignored": True},
        )
    monkeypatch.setattr(
        "backend.services.paypal_service.get_pending_shop_order",
        lambda _oid: None,
    )

    events.dispatch_order_webhook(
        {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "PAY-123"}},
        True,
    )
    assert captured == ["PAY-123"]
