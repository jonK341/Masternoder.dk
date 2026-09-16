"""
Smoke tests for shop v9.3 Sharpened Edges extension and trophies API.
"""
from pathlib import Path

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

ROOT = Path(__file__).resolve().parents[2]


def _get_app():
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True
    from backend.routes.shop_routes import shop_bp

    app.register_blueprint(shop_bp)
    return app


def test_shop_sharpened_css_file_exists():
    css = ROOT / "static" / "css" / "shop-sharpened.css"
    assert css.is_file()
    text = css.read_text(encoding="utf-8")
    assert "--shop-radius" in text
    assert ".shop-table-scroll" in text
    assert ".shop-site-hub" in text


def test_shop_index_imports_sharpened_css():
    html = (ROOT / "shop" / "index.html").read_text(encoding="utf-8")
    assert "shop-sharpened.css" in html
    assert "shop-site-hub" in html
    assert 'data-tab="trophies"' in html
    assert "shop-panel-trophies" in html


def test_shop_trophies_api():
    app = _get_app()
    with app.test_client() as c:
        r = c.get("/api/shop/trophies")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert data.get("on_chain_mint") is False
        items = data.get("items") or []
        assert len(items) >= 25
        sample = next(i for i in items if i.get("id") == "top25-01")
        assert sample.get("kind") == "trophy"
        assert sample.get("effective_price_usd") is not None


def test_shop_config_ui_version():
    app = _get_app()
    with app.test_client() as c:
        r = c.get("/api/shop/config")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("shop_ui_version") == "9.3.0"
