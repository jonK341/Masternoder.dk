"""MN2 health endpoint tests."""
from flask import Flask


def _app():
    from backend.routes.health_routes import health_bp
    app = Flask(__name__)
    app.register_blueprint(health_bp)
    return app


def test_api_health():
    c = _app().test_client()
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.get_json().get("success") is True


def test_mn2_health(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.health_check",
        lambda: {"success": True, "reachable": True, "status": "healthy", "block_height": 100},
    )
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.staking_health",
        lambda: {"status": "inactive", "staking_active": False, "mnsync": False},
    )
    monkeypatch.setattr(
        "backend.services.discord_service.outbox_stats",
        lambda limit=30: {"status": "unconfigured", "configured": False, "total_recent": 0, "failures_recent": 0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_network_stats.get_alerts",
        lambda limit=5: [],
    )
    c = _app().test_client()
    r = c.get("/api/mn2/health")
    assert r.status_code == 503  # degraded when minting inactive
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("status") == "degraded"
    comps = data.get("components", {})
    assert "discord_outbox" in comps
    assert "daemon_staking" in comps
    assert "network_alerts" in comps
    assert comps["daemon_staking"].get("status") == "inactive"
    assert comps["discord_outbox"].get("status") == "unconfigured"
    assert comps["network_alerts"].get("recent_count") == 0
