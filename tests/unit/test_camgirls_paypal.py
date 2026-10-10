"""Camgirls PayPal capture finish — no dumped APPROVED checkouts."""
from unittest.mock import patch, MagicMock

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_camgirls_webhook_captures_approved_pending(tmp_path, monkeypatch):
    from backend.services import camgirls_paypal_service as cg

    monkeypatch.setattr(cg, "_ORDERS_PATH", str(tmp_path / "camgirls_paypal_orders.json"))
    cg._write_orders({
        "pending": {
            "PP-CG-1": {
                "order_id": "PP-CG-1",
                "user_id": "buyer_cg",
                "action": "unlock",
                "performer_id": "performer_nova",
                "amount_mn2": 15,
                "amount_usd": 0.75,
            }
        },
        "captured": {},
    })

    with patch("backend.services.paypal_service.capture_order", return_value={
        "success": True, "order_id": "PP-CG-1", "capture_id": "CAP-CG-1", "amount": "0.75",
    }), patch("backend.services.camgirls_service.fulfill_external_payment", return_value={
        "success": True, "action": "unlock", "performer_id": "performer_nova",
    }):
        out = cg.handle_webhook(
            {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "PP-CG-1"}},
            True,
        )
    assert out.get("success") is True
    assert out.get("already_fulfilled") is not True
    rows = cg._read_orders()
    assert "PP-CG-1" in rows.get("captured", {})
    assert "PP-CG-1" not in (rows.get("pending") or {})


def test_camgirls_webhook_ignores_unknown_order(tmp_path, monkeypatch):
    from backend.services import camgirls_paypal_service as cg

    monkeypatch.setattr(cg, "_ORDERS_PATH", str(tmp_path / "camgirls_paypal_orders.json"))
    cg._write_orders({"pending": {}, "captured": {}})
    out = cg.handle_webhook(
        {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "NOPE"}},
        True,
    )
    assert out.get("success") is True
    assert out.get("ignored") is True


def test_camgirls_webhook_requires_signature(tmp_path, monkeypatch):
    from backend.services import camgirls_paypal_service as cg

    monkeypatch.setattr(cg, "_ORDERS_PATH", str(tmp_path / "camgirls_paypal_orders.json"))
    out = cg.handle_webhook({"event_type": "CHECKOUT.ORDER.APPROVED"}, False)
    assert out.get("success") is False
    assert "signature" in (out.get("error") or "").lower()


def test_dispatch_order_webhook_calls_camgirls(monkeypatch):
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
        lambda ev, signature_ok: seen.setdefault("camgirls", {"ok": signature_ok, "type": ev.get("event_type")}),
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
        {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": "PP-CG"}},
        True,
    )
    assert out.get("success") is True
    assert seen["camgirls"]["ok"] is True
    assert seen["camgirls"]["type"] == "CHECKOUT.ORDER.APPROVED"


def test_camgirls_fulfill_uses_pending_user_when_default(tmp_path, monkeypatch):
    from backend.services import camgirls_paypal_service as cg

    monkeypatch.setattr(cg, "_ORDERS_PATH", str(tmp_path / "camgirls_paypal_orders.json"))
    cg._write_orders({
        "pending": {
            "PP-CG-2": {
                "order_id": "PP-CG-2",
                "user_id": "real_buyer",
                "action": "unlock",
                "performer_id": "performer_luna",
                "amount_mn2": 12,
                "amount_usd": 0.6,
            }
        },
        "captured": {},
    })
    with patch("backend.services.paypal_service.capture_order", return_value={
        "success": True, "order_id": "PP-CG-2", "capture_id": "CAP-2",
    }), patch(
        "backend.services.camgirls_service.fulfill_external_payment",
        return_value={"success": True, "action": "unlock"},
    ) as fulfill:
        out = cg.fulfill_capture("PP-CG-2", user_id="default_user")
    assert out.get("success") is True
    assert fulfill.call_args[0][0] == "real_buyer"


def test_quote_fan_club_and_private_show():
    from backend.services.camgirls_paypal_service import quote_action

    fc = quote_action("fan_club", "performer_nova")
    assert fc.get("success") is True
    assert fc.get("amount_mn2") == 25

    ps = quote_action("private_show", "performer_nova", minutes=5)
    assert ps.get("success") is True
    assert ps.get("amount_mn2") == 25


def test_quote_tip_and_gift_actions():
    from backend.services.camgirls_paypal_service import quote_action

    tip = quote_action("tip", "performer_nova", amount_mn2=10)
    assert tip.get("success") is True
    assert tip.get("action") == "tip"
    assert tip.get("amount_mn2") == 10

    gift = quote_action("gift", "performer_nova", gift_id="rose")
    assert gift.get("success") is True
    assert gift.get("action") == "gift"
    assert gift.get("gift_id") == "rose"
    assert gift.get("amount_mn2") == 5


def test_fulfill_external_payment_gift_records_gift_id(tmp_path, monkeypatch):
    from backend.services import camgirls_service as svc

    age = tmp_path / "age.json"
    perf = tmp_path / "perf.json"
    tips = tmp_path / "tips.jsonl"
    monkeypatch.setattr(svc, "_AGE_FILE", str(age))
    monkeypatch.setattr(svc, "_PERFORMERS_FILE", str(perf))
    monkeypatch.setattr(svc, "_TIPS_FILE", str(tips))
    import json

    with open(perf, "w", encoding="utf-8") as f:
        json.dump({"performers": [{"id": "p1", "display_name": "T", "active": True, "tip_min_mn2": 5}]}, f)
    with open(age, "w", encoding="utf-8") as f:
        json.dump({"u1": {"verified_at": "2026-01-01"}}, f)

    out = svc.fulfill_external_payment("u1", "p1", "gift", 5, payment_ref="PP-X", gift_id="rose")
    assert out.get("success") is True
    assert tips.is_file()
    line = tips.read_text(encoding="utf-8").strip()
    row = json.loads(line)
    assert row.get("gift_id") == "rose"
    assert row.get("payment_method") == "paypal"
