"""Ledger customer control tests."""
import json
import pytest
from flask import Flask


def _app():
    from backend.routes.customer_aggregator_routes import customer_aggregator_bp
    app = Flask(__name__)
    app.register_blueprint(customer_aggregator_bp)
    return app


def test_assign_and_execute_ai_control(tmp_path, monkeypatch):
    controls_file = tmp_path / "ledger_customer_controls.json"
    controls_file.write_text(json.dumps({"version": 1, "assignments": {}}), encoding="utf-8")

    import backend.services.ledger_customer_control_service as lcc
    monkeypatch.setattr(lcc, "_CONTROLS_FILE", str(controls_file))

    points_dir = tmp_path / "unified_points"
    points_dir.mkdir()
    (points_dir / "user_a.json").write_text(
        json.dumps({"user_id": "user_a", "level": 1, "coins": 0, "mn2_balance": 0.5}),
        encoding="utf-8",
    )

    import backend.services.customer_aggregator_service as cas
    monkeypatch.setattr(cas, "_POINTS_DIR", str(points_dir))
    monkeypatch.setattr(lcc, "_BASE", str(tmp_path))

    assigned = lcc.assign_controller("user_a", "ai", notes="test")
    assert assigned.get("success") is True
    assert lcc.get_assignment("user_a")["controller_type"] == "ai"

    def _fake_panel(uid):
        return {"success": True, "user_id": uid, "ai_assessment": "ok"}

    monkeypatch.setattr("backend.services.ai_user_controller.ai_control_panel", _fake_panel)
    result = lcc.execute_control_action("user_a", "control_panel")
    assert result.get("success") is True
    assert result.get("result", {}).get("ai_assessment") == "ok"


def test_ledger_customer_route_localhost(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    controls_file = tmp_path / "ledger_customer_controls.json"
    controls_file.write_text(json.dumps({"version": 1, "assignments": {}}), encoding="utf-8")

    import backend.services.ledger_customer_control_service as lcc
    monkeypatch.setattr(lcc, "_CONTROLS_FILE", str(controls_file))

    points_dir = tmp_path / "unified_points"
    points_dir.mkdir()
    (points_dir / "cust_b.json").write_text(
        json.dumps({"user_id": "cust_b", "level": 2, "coins": 10, "mn2_balance": 1.0}),
        encoding="utf-8",
    )

    import backend.services.customer_aggregator_service as cas
    monkeypatch.setattr(cas, "_POINTS_DIR", str(points_dir))
    monkeypatch.setattr(lcc, "_BASE", str(tmp_path))

    monkeypatch.setattr("backend.services.mn2_ledger.get_entries_by_user", lambda uid, limit=25: [])
    monkeypatch.setattr(
        "backend.services.encoder_order_service.list_orders",
        lambda uid, limit=50: {"success": True, "orders": []},
    )
    monkeypatch.setattr(
        "backend.services.ai_user_controller.ai_control_panel",
        lambda uid: {"success": True, "user_id": uid},
    )
    monkeypatch.setattr(
        "backend.services.aggregator_mn2_service.get_user_stats",
        lambda uid: {"success": True, "earned_today_mn2": 0},
    )

    c = _app().test_client()
    r = c.get("/api/customers/cust_b/ledger", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("customer", {}).get("user_id") == "cust_b"
