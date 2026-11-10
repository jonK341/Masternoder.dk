"""Landing monitor snapshot + rotation."""
from __future__ import annotations

from flask import Flask


def test_landing_monitor_snapshot_shape(tmp_path, monkeypatch):
    from backend.services import landing_monitor_service as svc

    monkeypatch.setattr(svc, "_CACHE_PATH", str(tmp_path / "landing_monitor_cache.json"))
    monkeypatch.setattr(svc, "_collect_stats", lambda: {
        "total_videos": 3,
        "total_users": 2,
        "total_achievements": 1,
        "total_battles": 4,
        "mn2_usd_price": 0.01,
        "daemon_ok": True,
        "block_height": 100,
    })
    payload = svc.refresh_snapshot(force=True)
    assert payload["success"] is True
    assert payload["bpm"] == 180
    assert payload["refresh_ms"] == 5000
    assert payload["stats"]["total_videos"] == 3
    assert payload["special"]["id"]
    assert payload["lightshow"]["id"]
    assert "explain" in payload["lightshow"]
    assert payload["effect_explain"]["bpm"] == 180
    assert payload["music"]["bpm"] == 180
    again = svc.get_snapshot(max_age_sec=30)
    assert again["stats"]["total_users"] == 2


def test_landing_monitor_route():
    from backend.routes.landing_monitor_routes import landing_monitor_bp
    from backend.services import landing_monitor_service as svc

    app = Flask(__name__)
    app.register_blueprint(landing_monitor_bp)
    # Avoid DB by forcing a cache hit from a synthetic refresh
    svc.refresh_snapshot = lambda force=False: {
        "success": True,
        "bpm": 180,
        "refresh_ms": 5000,
        "stats": {"total_videos": 0},
        "special": {"id": "wallet", "title": "t"},
        "lightshow": {"id": "pulse", "explain": "e"},
        "effect_explain": {"title": "Pulse", "body": "e", "bpm": 180},
        "music": {"bpm": 180},
        "updated_at": "Z",
    }
    c = app.test_client()
    r = c.get("/api/landing/monitor")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["bpm"] == 180
