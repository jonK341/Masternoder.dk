"""Customer aggregator tests."""
import os

import pytest
from flask import Flask


def _app():
    from backend.routes.customer_aggregator_routes import customer_aggregator_bp
    app = Flask(__name__)
    app.register_blueprint(customer_aggregator_bp)
    return app


def test_customers_requires_admin(monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    c = _app().test_client()
    r = c.get("/api/customers", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403


def test_customers_list_localhost(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    base = tmp_path / "app"
    db = upd.UnifiedPointsDatabase(base_dir=str(base))
    db.add_points("cust_a", "mn2_balance", 1.0, source="seed", metadata={"reference": "c1"})

    import backend.services.customer_aggregator_service as cas
    monkeypatch.setattr(cas, "_POINTS_DIR", db.points_dir)

    c = _app().test_client()
    r = c.get("/api/customers?limit=5", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("total", 0) >= 0


def test_customers_list_with_ops_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCORD_OPS_SECRET", "unit-test-ops-secret")
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)

    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    base = tmp_path / "app"
    db = upd.UnifiedPointsDatabase(base_dir=str(base))
    db.add_points("cust_b", "mn2_balance", 2.0, source="seed", metadata={"reference": "c2"})

    import backend.services.customer_aggregator_service as cas
    monkeypatch.setattr(cas, "_POINTS_DIR", db.points_dir)

    c = _app().test_client()
    r = c.get(
        "/api/customers?limit=5",
        headers={"X-Ops-Secret": "unit-test-ops-secret"},
        environ_overrides={"REMOTE_ADDR": "8.8.8.8"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True


def test_customer_event_emits(tmp_path, monkeypatch):
    import backend.services.customer_aggregator_service as cas
    import backend.services.activity_events_service as aes

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(aes, "_LOG_PATH", str(log_dir / "activity_events.jsonl"))
    monkeypatch.setattr(cas, "_ACTIVE_DEBOUNCE_PATH", str(log_dir / "customer_active_emit.json"))
    monkeypatch.setattr(cas, "_POINTS_DIR", str(tmp_path / "points"))
    os.makedirs(cas._POINTS_DIR, exist_ok=True)

    cas.emit_customer_new("user_alpha")
    cas.emit_customer_active("user_alpha", source="test")
    cas.emit_customer_active("user_alpha", source="test")

    rows = aes.recent(limit=10)
    types = [r.get("type") for r in rows]
    assert "customer_new" in types
    assert types.count("customer_active") == 1
