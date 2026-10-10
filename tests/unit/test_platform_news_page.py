"""Platform news API tests."""
from flask import Flask


def _app():
    from backend.routes.platform_news_routes import platform_news_bp
    app = Flask(__name__)
    app.register_blueprint(platform_news_bp)
    return app


def test_platform_news_list():
    c = _app().test_client()
    r = c.get("/api/news/platform?limit=5")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert isinstance(data.get("news"), list)


def test_platform_news_channel_filter():
    c = _app().test_client()
    r = c.get("/api/news/platform?channel=casino&limit=10")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    for item in data.get("news") or []:
        ch = (item.get("channel") or item.get("category") or "").lower()
        assert ch == "casino"


def test_platform_news_channels():
    c = _app().test_client()
    r = c.get("/api/news/channels")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert isinstance(data.get("channels"), list)
