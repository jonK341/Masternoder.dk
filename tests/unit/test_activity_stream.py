"""Activity stream / recent API tests."""
from flask import Flask


def test_activity_recent_returns_json():
    from backend.routes.activity_stream_routes import activity_stream_bp

    app = Flask(__name__)
    app.register_blueprint(activity_stream_bp)
    client = app.test_client()
    r = client.get("/api/activity/recent?limit=5")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert isinstance(data.get("events"), list)


def test_activity_feed_service():
    from backend.services.activity_feed_service import recent_activity

    events = recent_activity(limit=3)
    assert isinstance(events, list)
