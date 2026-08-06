"""Activity stream / recent API tests."""
from flask import Flask


def _app():
    from backend.routes.activity_stream_routes import activity_stream_bp

    app = Flask(__name__)
    app.register_blueprint(activity_stream_bp)
    return app


def test_activity_recent_returns_json():
    client = _app().test_client()
    r = client.get("/api/activity/recent?limit=5")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert isinstance(data.get("events"), list)


def test_activity_monitor_returns_tiles():
    client = _app().test_client()
    r = client.get("/api/activity/monitor")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    tiles = data.get("tiles") or {}
    assert "customers" in tiles
    assert "discord" in tiles
    assert "news" in tiles
    assert isinstance(data.get("recent_events"), list)


def test_activity_feed_service():
    from backend.services.activity_feed_service import recent_activity

    events = recent_activity(limit=3)
    assert isinstance(events, list)


def test_activity_monitor_service():
    from backend.services.activity_monitor_service import get_monitor_status

    status = get_monitor_status()
    assert status.get("success") is True
    assert "tiles" in status
    assert "stream" in status
