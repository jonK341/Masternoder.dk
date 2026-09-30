"""Encoder customer fulfillment tests."""
import json
import pytest
from flask import Flask


def _app():
    from backend.routes.customer_aggregator_routes import customer_aggregator_bp
    app = Flask(__name__)
    app.register_blueprint(customer_aggregator_bp)
    return app


def test_fulfill_single_customer(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    base = tmp_path / "app"
    fulfill_file = base / "data" / "encoder_customer_fulfillment.json"
    fulfill_file.parent.mkdir(parents=True)
    fulfill_file.write_text(json.dumps({"version": 1, "fulfilled": {}}), encoding="utf-8")

    points_dir = base / "logs" / "unified_points"
    points_dir.mkdir(parents=True)

    import backend.services.encoder_customer_fulfillment_service as ecf
    import backend.services.ledger_customer_control_service as lcc

    monkeypatch.setattr(ecf, "_FULFILLMENT_FILE", str(fulfill_file))
    monkeypatch.setattr(ecf, "_BASE", str(base))
    monkeypatch.setattr(lcc, "_BASE", str(base))

    import backend.services.customer_aggregator_service as cas
    monkeypatch.setattr(cas, "_POINTS_DIR", str(points_dir))
    monkeypatch.setattr(ecf, "_promote_customer_row", lambda uid, **kw: None)

    def _fake_onboard(uid, username=""):
        return {"success": True, "user_id": uid, "actions": ["stub"]}

    def _fake_micro(uid, actions=None, meta=None):
        return {"success": True, "total_mn2_awarded": 0.002, "awarded_count": 2, "results": []}

    monkeypatch.setattr("backend.services.ai_user_controller.onboard_new_user", _fake_onboard)
    monkeypatch.setattr("backend.services.encoder_micro_rewards_service.attach_micro_rewards", _fake_micro)
    monkeypatch.setattr(
        "backend.services.encoder_v2_service.ensure_free_unlocks",
        lambda uid: {"success": True, "added": 12, "progress": {"unlocked_count": 12}},
    )

    res = ecf.fulfill_single_customer(
        "discord_123",
        discord_meta={"discord_id": "123", "username": "tester"},
    )
    assert res.get("success") is True
    assert ecf.is_fulfilled("discord_123") is True


def test_customer_fulfillment_encoder_order(tmp_path, monkeypatch):
    import backend.services.encoder_order_service as eos
    import backend.services.encoder_customer_fulfillment_service as ecf

    orders_file = tmp_path / "encoder_orders.json"
    orders_file.write_text(json.dumps({"version": 1, "orders": []}), encoding="utf-8")
    monkeypatch.setattr(eos, "_ORDERS_FILE", str(orders_file))
    monkeypatch.setattr(eos, "_BASE", str(tmp_path))

    fulfill_file = tmp_path / "encoder_customer_fulfillment.json"
    fulfill_file.write_text(json.dumps({"version": 1, "fulfilled": {}}), encoding="utf-8")
    monkeypatch.setattr(ecf, "_FULFILLMENT_FILE", str(fulfill_file))

    def _fake_fulfill(uid, **kwargs):
        return {"success": True, "user_id": uid, "actions": ["test"]}

    monkeypatch.setattr(ecf, "fulfill_single_customer", _fake_fulfill)

    q = eos.quote_order("customer_fulfillment", {})
    assert q.get("success") is True
    assert q.get("price_mn2") == 0.0

    created = eos.create_balance_order("discord_99", "customer_fulfillment", {"discord_id": "99"}, auto_fulfill=True)
    assert created.get("success") is True
    assert created.get("order", {}).get("status") == "fulfilled"


def test_fulfill_discord_route_requires_admin(monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    c = _app().test_client()
    r = c.post("/api/customers/fulfill/discord", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403
