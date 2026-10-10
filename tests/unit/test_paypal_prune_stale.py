"""Prune ghost PayPal pending rows when checkout no longer exists at PayPal."""
from __future__ import annotations


def test_prune_stale_dry_run_flags_not_found(monkeypatch):
    from backend.services import paypal_order_events as events

    job = {
        "rail": "onramp",
        "local_id": "q_test",
        "paypal_order_id": "PAY-GONE",
        "user_id": "u1",
    }
    monkeypatch.setattr(events, "collect_pending_paypal_jobs", lambda extra=None: [job])
    monkeypatch.setattr(
        "backend.services.paypal_service.get_checkout_order",
        lambda oid: {
            "success": False,
            "error": '{"name":"RESOURCE_NOT_FOUND","details":[{"issue":"INVALID_RESOURCE_ID"}]}',
        },
    )

    out = events.prune_stale_paypal_pending_orders(limit=10, dry_run=True)
    assert out["counts"]["pruned"] == 1
    assert out["results"][0]["outcome"] == "would_prune"


def test_expire_onramp_pending(monkeypatch, tmp_path):
    from backend.services import mn2_onramp_service as onramp

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    orders = {
        "q1": {
            "order_id": "q1",
            "user_id": "u1",
            "status": "pending_payment",
            "paypal_order_id": "PAY1",
        },
    }
    (data_dir / "mn2_onramp_orders.json").write_text(
        __import__("json").dumps(orders),
        encoding="utf-8",
    )
    monkeypatch.setattr(onramp, "_data_dir", lambda: str(data_dir))

    from backend.services.paypal_order_events import expire_pending_paypal_job

    res = expire_pending_paypal_job(
        {"rail": "onramp", "local_id": "q1", "paypal_order_id": "PAY1"},
        "paypal_not_found",
    )
    assert res.get("success") is True
    saved = __import__("json").loads((data_dir / "mn2_onramp_orders.json").read_text(encoding="utf-8"))
    assert saved["q1"]["status"] == "expired"
    assert saved["q1"]["paypal_prune_reason"] == "paypal_not_found"
