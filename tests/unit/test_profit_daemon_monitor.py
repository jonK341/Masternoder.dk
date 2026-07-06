"""Profit daemon monitor API — public/owner views, heartbeat, instances."""
from __future__ import annotations

import pytest


ADMIN_KEY = "test-admin-key"


@pytest.fixture()
def client(monkeypatch):
    from backend.routes.profit_daemon_routes import profit_daemon_bp
    from flask import Flask

    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", ADMIN_KEY)
    app = Flask(__name__)
    app.register_blueprint(profit_daemon_bp)
    return app.test_client()


def test_profit_daemon_status_route_public(client):
    rv = client.get("/api/profit-daemon/status")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("success") is True
    assert "loops" in data
    assert data.get("view") == "public"
    # Sanitized: no funding/host/server detail for anonymous callers.
    assert "venues" not in data
    assert "host" not in data
    assert "server" not in data
    cats = {s.get("category") for s in data.get("stats") or []}
    assert not cats & {"funding", "treasury", "payout"}
    payout = data.get("payout") or {}
    assert "paypal_sweepable_usd" not in payout
    inst = data.get("daemon_instances") or {}
    assert set(inst) <= {"active_count", "conflict", "conflict_reason"}


def test_profit_daemon_status_route_owner(client):
    rv = client.get(
        "/api/profit-daemon/status",
        headers={"X-Exchange-Admin-Key": ADMIN_KEY},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("view") == "owner"
    assert "venues" in data
    assert "server" in data
    payout = data.get("payout") or {}
    assert "paypal_sweepable_usd" in payout


def test_profit_daemon_status_bad_key_gets_public(client):
    rv = client.get(
        "/api/profit-daemon/status",
        headers={"X-Exchange-Admin-Key": "wrong-key"},
    )
    assert rv.status_code == 200
    assert rv.get_json().get("view") == "public"


def test_monitor_status_structure():
    from backend.services.profit_daemon_monitor_service import monitor_status
    st = monitor_status()
    assert st.get("success") is True
    assert isinstance(st.get("loops"), list)
    assert isinstance(st.get("stats"), list)
    assert st.get("stat_count", 0) >= 31
    assert "blockers" in st
    assert "profit_readiness_pct" in st
    assert "daemon_instances" in st


def test_sanitize_status_public_strips_sensitive():
    from backend.services.profit_daemon_monitor_service import (
        monitor_status,
        sanitize_status_public,
    )
    full = monitor_status()
    pub = sanitize_status_public(full)
    assert pub["view"] == "public"
    ids = {s.get("id") for s in pub.get("stats") or []}
    assert not ids & {"binance_usdc", "nonkyc_usdt", "live_stash", "sweepable_usd"}
    # Operational health preserved.
    assert "profit_readiness_pct" in pub
    assert any(s.get("id") == "daemon_online" for s in pub["stats"])


def test_heartbeat_requires_admin(client):
    rv = client.post("/api/profit-daemon/heartbeat", json={"instance_id": "x"})
    assert rv.status_code == 401


def test_instances_requires_admin(client):
    rv = client.get("/api/profit-daemon/instances")
    assert rv.status_code == 401


def test_heartbeat_and_instances_roundtrip(client, tmp_path, monkeypatch):
    import backend.services.profit_daemon_instance_service as inst

    monkeypatch.setattr(inst, "_INSTANCES_FILE", str(tmp_path / "instances.json"))

    headers = {"X-Exchange-Admin-Key": ADMIN_KEY}
    rv = client.post(
        "/api/profit-daemon/heartbeat",
        json={"instance_id": "laptop-123", "host": "laptop", "mode": "paper",
              "profile": "max", "source": "remote", "pid": 123},
        headers=headers,
    )
    assert rv.status_code == 200
    assert rv.get_json()["success"] is True

    rv = client.get("/api/profit-daemon/instances", headers=headers)
    assert rv.status_code == 200
    data = rv.get_json()
    rows = data.get("instances") or []
    assert any(r.get("instance_id") == "laptop-123" and r.get("active") for r in rows)
    assert data.get("active_count") == 1
    assert data.get("conflict") is False


def test_conflict_detection(tmp_path, monkeypatch):
    import backend.services.profit_daemon_instance_service as inst

    monkeypatch.setattr(inst, "_INSTANCES_FILE", str(tmp_path / "instances.json"))
    inst.report_instance({"instance_id": "server-1", "host": "server", "mode": "live"})
    inst.report_instance({"instance_id": "laptop-2", "host": "laptop", "mode": "live"})
    summary = inst.instances_summary()
    assert summary["active_count"] == 2
    assert summary["conflict"] is True
    assert summary["live_active_count"] == 2
    assert "duplicate" in (summary["conflict_reason"] or "")


def test_heartbeat_rejects_missing_instance_id(tmp_path, monkeypatch):
    import backend.services.profit_daemon_instance_service as inst

    monkeypatch.setattr(inst, "_INSTANCES_FILE", str(tmp_path / "instances.json"))
    out = inst.report_instance({})
    assert out["success"] is False
