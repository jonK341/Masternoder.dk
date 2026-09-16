"""Camgirls studio feature tests."""
from flask import Flask

from backend.routes.camgirls_routes import camgirls_bp
from backend.services.camgirls_studio_service import studio_catalog


def test_studio_catalog():
    cat = studio_catalog()
    assert cat.get("success") is True
    assert "tip_menu" in (cat.get("standard_program_features") or [])
    assert "rose" in (cat.get("gifts") or {})


def test_studio_catalog_route():
    app = Flask(__name__)
    app.register_blueprint(camgirls_bp)
    client = app.test_client()
    r = client.get("/api/camgirls/studio/catalog")
    assert r.status_code == 200
    data = r.get_json() or {}
    assert data.get("success") is True
    assert len(data.get("dances") or {}) >= 3
