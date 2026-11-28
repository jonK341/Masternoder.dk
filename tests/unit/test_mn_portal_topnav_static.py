"""Static Portals topnav fragment + single-page include."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_static_portal_topnav_html_exists_and_has_portals():
    html = (ROOT / "static/html/mn-portal-topnav.html").read_text(encoding="utf-8")
    assert 'id="navToolbar"' in html
    assert 'id="navPortalTrigger"' in html
    assert 'id="navPortalPanel"' in html
    assert "data-mn-portal-static" in html
    assert "Play portals" in html
    assert 'data-page-id="shop"' in html
    assert 'data-page-id="exchange"' in html


def test_portal_topnav_include_script_exists():
    js = (ROOT / "static/js/mn-portal-topnav.js").read_text(encoding="utf-8")
    assert "mn-portal-topnav.html" in js
    assert "MN_PORTAL_TOPNAV_STATIC" in js
    assert "navigation-toolbar.js" in js


def test_home_and_shop_use_single_include():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    shop = (ROOT / "shop/index.html").read_text(encoding="utf-8")
    assert "mn-portal-topnav.js" in home
    assert "mn-portal-topnav.js" in shop
    assert "navigation-toolbar.js" not in home
    assert "navigation-toolbar.js" not in shop
