"""Camgirls studio feature tests."""
from flask import Flask

from backend.routes.camgirls_routes import camgirls_bp
from backend.services.camgirls_studio_service import studio_catalog


def test_studio_catalog():
    cat = studio_catalog()
    assert cat.get("success") is True
    assert "tip_menu" in (cat.get("standard_program_features") or [])
    assert "rose" in (cat.get("gifts") or {})


def test_tip_with_gift_requires_unlock():
    from tests.unit.test_camgirls_service import CamgirlsTestBase
    from backend.services.camgirls_studio_service import tip_with_gift
    from backend.services.camgirls_service import record_age_verification

    t = CamgirlsTestBase()
    t.setUp()
    try:
        record_age_verification("buyer", birth_year=1990)
        blocked = tip_with_gift("buyer", "p1", gift_id="rose")
        assert blocked.get("code") == "unlock_required"
    finally:
        t.tearDown()


def test_tip_with_gift_after_unlock():
    from tests.unit.test_camgirls_service import CamgirlsTestBase
    from backend.services.camgirls_studio_service import tip_with_gift
    from backend.services.camgirls_service import record_age_verification, unlock_performer

    t = CamgirlsTestBase()
    t.setUp()
    try:
        t._credit("buyer", 50.0)
        record_age_verification("buyer", birth_year=1990)
        unlock_performer("buyer", "p1")
        ok = tip_with_gift("buyer", "p1", gift_id="rose")
        assert ok.get("success") is True
        assert ok.get("gift_id") == "rose"
    finally:
        t.tearDown()


def test_studio_catalog_route():
    app = Flask(__name__)
    app.register_blueprint(camgirls_bp)
    client = app.test_client()
    r = client.get("/api/camgirls/studio/catalog")
    assert r.status_code == 200
    data = r.get_json() or {}
    assert data.get("success") is True
    assert len(data.get("dances") or {}) >= 3
