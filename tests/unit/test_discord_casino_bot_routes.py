"""Social platform hub route registration."""
from __future__ import annotations

from flask import Flask


def test_platforms_hub_route():
    from backend.routes.social_platform_routes import social_platform_bp

    app = Flask(__name__)
    app.register_blueprint(social_platform_bp)
    with app.test_client() as client:
        r = client.get("/api/social/platforms/hub")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        ids = [p.get("id") for p in data.get("platforms") or []]
        assert "discord" in ids


def test_discord_play_page_registered():
    from backend.routes.all_page_routes import all_page_bp, PAGES

    assert "discord-play" in PAGES
    app = Flask(__name__)
    app.register_blueprint(all_page_bp)
    with app.test_client() as client:
        r = client.get("/discord-play/")
        assert r.status_code == 200
