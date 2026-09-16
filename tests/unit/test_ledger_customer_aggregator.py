"""Ledger customer aggregator — sync and agent assignment tests."""
import json
import pytest
from flask import Flask


def _app():
    from backend.routes.customer_aggregator_routes import customer_aggregator_bp
    app = Flask(__name__)
    app.register_blueprint(customer_aggregator_bp)
    return app


def _ledger_rows():
    return [
        {
            "user_id": "ledger_user_1",
            "entry_count": 3,
            "last_activity": "2026-09-16T10:00:00Z",
            "ledger_in_mn2": 1.5,
            "ledger_out_mn2": 0.2,
            "ledger_net_mn2": 1.3,
            "entry_types": ["deposit", "shop_payment"],
        },
        {
            "user_id": "ledger_user_2",
            "entry_count": 1,
            "last_activity": "2026-09-15T08:00:00Z",
            "ledger_in_mn2": 0.5,
            "ledger_out_mn2": 0.0,
            "ledger_net_mn2": 0.5,
            "entry_types": ["deposit"],
        },
    ]


def test_sync_ledger_creates_points_stubs(tmp_path, monkeypatch):
    points_dir = tmp_path / "unified_points"
    points_dir.mkdir()
    controls_file = tmp_path / "ledger_customer_controls.json"
    controls_file.write_text(json.dumps({"version": 1, "assignments": {}}), encoding="utf-8")

    import backend.services.ledger_customer_aggregator_service as lca
    import backend.services.ledger_customer_control_service as lcc
    import backend.services.customer_aggregator_service as cas

    monkeypatch.setattr(lca, "_POINTS_DIR", str(points_dir))
    monkeypatch.setattr(lca, "_BASE", str(tmp_path))
    monkeypatch.setattr(lcc, "_CONTROLS_FILE", str(controls_file))
    monkeypatch.setattr(lcc, "_BASE", str(tmp_path))
    monkeypatch.setattr(cas, "_POINTS_DIR", str(points_dir))
    monkeypatch.setattr(
        "backend.services.mn2_ledger.list_ledger_user_summaries",
        lambda limit=5000: _ledger_rows(),
    )

    result = lca.sync_ledger_customers_to_aggregator(limit=10)
    assert result.get("success") is True
    assert result.get("stubs_created") == 2
    assert (points_dir / "ledger_user_1.json").is_file()
    raw = json.loads((points_dir / "ledger_user_1.json").read_text(encoding="utf-8"))
    assert raw.get("source") == "ledger"
    assert raw.get("ledger", {}).get("entry_count") == 3


def test_assign_agents_round_robin(tmp_path, monkeypatch):
    points_dir = tmp_path / "unified_points"
    points_dir.mkdir()
    controls_file = tmp_path / "ledger_customer_controls.json"
    controls_file.write_text(json.dumps({"version": 1, "assignments": {}}), encoding="utf-8")

    import backend.services.ledger_customer_aggregator_service as lca
    import backend.services.ledger_customer_control_service as lcc

    monkeypatch.setattr(lca, "_POINTS_DIR", str(points_dir))
    monkeypatch.setattr(lca, "_BASE", str(tmp_path))
    monkeypatch.setattr(lcc, "_CONTROLS_FILE", str(controls_file))
    monkeypatch.setattr(lcc, "_BASE", str(tmp_path))
    monkeypatch.setattr(
        "backend.services.mn2_ledger.list_ledger_user_summaries",
        lambda limit=5000: _ledger_rows(),
    )
    monkeypatch.setattr(
        lca,
        "list_available_agents",
        lambda: {
            "success": True,
            "agents": [
                {"agent_id": "agent_a", "status": "active"},
                {"agent_id": "agent_b", "status": "active"},
            ],
            "default_agent_id": "agent_a",
        },
    )

    result = lca.assign_agents_to_ledger_customers(limit=10, only_unassigned=True)
    assert result.get("success") is True
    assert result.get("assigned_count") == 2
    assert lcc.get_assignment("ledger_user_1")["controller_type"] == "agent"
    assert lcc.get_assignment("ledger_user_2")["controller_type"] == "agent"


def test_list_customers_includes_ledger_source(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    monkeypatch.delenv("YOUR_OPS_SECRET", raising=False)

    points_dir = tmp_path / "unified_points"
    points_dir.mkdir()

    import backend.services.customer_aggregator_service as cas
    monkeypatch.setattr(cas, "_POINTS_DIR", str(points_dir))
    monkeypatch.setattr(
        "backend.services.mn2_ledger.list_ledger_user_summaries",
        lambda limit=5000: _ledger_rows(),
    )

    c = _app().test_client()
    r = c.get("/api/customers?limit=10&source=ledger", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    ids = {row["user_id"] for row in (data.get("customers") or [])}
    assert "ledger_user_1" in ids
    assert "ledger_user_2" in ids


def test_sync_ledger_agents_route(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    monkeypatch.delenv("YOUR_OPS_SECRET", raising=False)

    points_dir = tmp_path / "unified_points"
    points_dir.mkdir()
    controls_file = tmp_path / "ledger_customer_controls.json"
    controls_file.write_text(json.dumps({"version": 1, "assignments": {}}), encoding="utf-8")

    import backend.services.ledger_customer_aggregator_service as lca
    import backend.services.ledger_customer_control_service as lcc

    monkeypatch.setattr(lca, "_POINTS_DIR", str(points_dir))
    monkeypatch.setattr(lca, "_BASE", str(tmp_path))
    monkeypatch.setattr(lcc, "_CONTROLS_FILE", str(controls_file))
    monkeypatch.setattr(lcc, "_BASE", str(tmp_path))
    monkeypatch.setattr(
        "backend.services.mn2_ledger.list_ledger_user_summaries",
        lambda limit=5000: _ledger_rows(),
    )
    monkeypatch.setattr(
        lca,
        "list_available_agents",
        lambda: {
            "success": True,
            "agents": [{"agent_id": "master_fix", "status": "active"}],
            "default_agent_id": "master_fix",
        },
    )

    c = _app().test_client()
    r = c.post(
        "/api/customers/sync/ledger-agents",
        json={"limit": 10},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("ledger_sync", {}).get("stubs_created") == 2
    assert data.get("agent_assign", {}).get("assigned_count") == 2
