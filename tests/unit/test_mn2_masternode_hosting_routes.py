"""Masternode hosting routes — health probe and auth gates."""
from __future__ import annotations

import json

import pytest
from flask import Flask

from backend.routes.mn2_masternode_routes import mn2_masternode_bp, _guest_user


@pytest.fixture
def mn_host_client():
    app = Flask(__name__)
    app.register_blueprint(mn2_masternode_bp)
    return app.test_client()


def test_guest_user_detection():
    assert _guest_user("") is True
    assert _guest_user("default_user") is True
    assert _guest_user("anon_abc") is True
    assert _guest_user("real_user_1") is False


def test_health_endpoint(monkeypatch, mn_host_client):
    from backend.services import mn2_masternode_service as mn
    from backend.services import mn2_masternode_hosting_service as hosting

    monkeypatch.setattr(mn, "probe_health", lambda: {"status": "healthy", "enabled": True})
    monkeypatch.setattr(hosting, "hosting_stats", lambda: {"paid_orders": 2, "pending_orders": 0})

    rv = mn_host_client.get("/api/mn2/masternode/health")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["success"] is True
    assert data["status"] == "healthy"
    assert data["service"] == "mn2_masternode_hosting"


def test_health_degraded_returns_503(monkeypatch, mn_host_client):
    from backend.services import mn2_masternode_service as mn
    from backend.services import mn2_masternode_hosting_service as hosting

    monkeypatch.setattr(mn, "probe_health", lambda: {"status": "degraded", "error": "rpc down"})
    monkeypatch.setattr(hosting, "hosting_stats", lambda: {})

    rv = mn_host_client.get("/api/mn2/masternode/health")
    assert rv.status_code == 503
    assert rv.get_json()["status"] == "degraded"


def test_checkout_quote_requires_auth(mn_host_client, monkeypatch):
    monkeypatch.setattr(
        "backend.routes.mn2_masternode_routes.resolve_user_id",
        lambda **kw: "default_user",
    )
    rv = mn_host_client.post(
        "/api/mn2/masternode/checkout/quote",
        json={"slots": 1},
        content_type="application/json",
    )
    assert rv.status_code == 401
    body = rv.get_json()
    assert body["success"] is False
    assert body["code"] == "auth_required"


def test_checkout_status_idor_forbidden(mn_host_client, monkeypatch, tmp_path):
    from backend.services import mn2_masternode_hosting_service as hosting

    orders_path = tmp_path / "mn2_masternode_orders.json"
    orders_path.write_text(
        json.dumps({
            "mnq_other": {
                "order_id": "mnq_other",
                "user_id": "owner_a",
                "status": "quoted",
                "slots": 1,
            }
        }),
        encoding="utf-8",
    )

    def _data_path(name: str) -> str:
        if name == hosting._ORDERS_FILE:
            return str(orders_path)
        return str(tmp_path / name)

    monkeypatch.setattr(hosting, "_data_path", _data_path)

    monkeypatch.setattr(
        "backend.routes.mn2_masternode_routes.resolve_user_id",
        lambda **kw: "intruder_b",
    )
    rv = mn_host_client.get("/api/mn2/masternode/checkout/status?order_id=mnq_other")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["success"] is False
    assert body["error"] == "Forbidden"


def test_my_orders_requires_auth(mn_host_client, monkeypatch):
    monkeypatch.setattr(
        "backend.routes.mn2_masternode_routes.resolve_user_id",
        lambda **kw: "default_user",
    )
    rv = mn_host_client.get("/api/mn2/masternode/my-orders")
    assert rv.status_code == 401
    assert rv.get_json()["error"] == "auth_required"
