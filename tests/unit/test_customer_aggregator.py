"""Customer aggregator tests."""
import pytest
from flask import Flask


def _app():
    from backend.routes.customer_aggregator_routes import customer_aggregator_bp
    app = Flask(__name__)
    app.register_blueprint(customer_aggregator_bp)
    return app


def test_customers_requires_admin(monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    c = _app().test_client()
    r = c.get("/api/customers", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403


def test_customers_list_localhost(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
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
