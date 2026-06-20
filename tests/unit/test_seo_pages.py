"""Tier C4 — SEO landing pages and sitemap."""
from flask import Flask


def _pages_app():
    from backend.routes.all_page_routes import all_page_bp

    app = Flask(__name__)
    app.register_blueprint(all_page_bp)
    return app


def test_hosting_landing_page():
    r = _pages_app().test_client().get("/hosting/")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "MN2 Masternode Hosting" in body
    assert 'rel="canonical"' in body
    assert "application/ld+json" in body
    assert "/shop?tab=mn2" in body


def test_sitemap_xml():
    r = _pages_app().test_client().get("/sitemap.xml")
    assert r.status_code == 200
    assert "application/xml" in (r.content_type or "")
    text = r.get_data(as_text=True)
    assert "/hosting/" in text
    assert "/generator/" in text
    assert "/camgirls/" in text


def test_robots_txt():
    r = _pages_app().test_client().get("/robots.txt")
    assert r.status_code == 200
    text = r.get_data(as_text=True)
    assert "Sitemap:" in text
    assert "/sitemap.xml" in text
