"""Shop storefront assets and wiring (HTML references external CSS/JS)."""
from pathlib import Path

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

ROOT = Path(__file__).resolve().parents[2]


def test_shop_storefront_assets_exist():
    assert (ROOT / "static/css/shop.css").is_file()
    assert (ROOT / "static/js/shop-profile-manager.js").is_file()


def test_shop_index_links_storefront():
    html = (ROOT / "shop/index.html").read_text(encoding="utf-8")
    assert "shop-storefront" in html
    assert "/static/css/shop.css" in html
    assert "shop-profile-manager.js" in html
    assert 'id="shop-panel-profile"' in html
    assert 'data-tab="profile"' in html
    assert html.count('class="shop-idea"') == 10
    assert "<style>" not in html


def test_profile_links_shop_profile_manager():
    html = (ROOT / "profile/index.html").read_text(encoding="utf-8")
    assert "/shop#shop-profile" in html
    assert "/static/css/shop.css" in html
