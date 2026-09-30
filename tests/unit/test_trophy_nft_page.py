"""NFT gallery presentation for the trophies page."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TROPHIES_HTML = (ROOT / "trophies" / "index.html").read_text(encoding="utf-8")
NFT_JS = ROOT / "static" / "js" / "trophy-nft.js"
NFT_CSS = ROOT / "static" / "css" / "trophies-nft-theme.css"


def test_trophies_page_loads_nft_theme_assets():
    assert 'href="/static/css/trophies-nft-theme.css' in TROPHIES_HTML
    assert 'src="/static/js/trophy-nft.js' in TROPHIES_HTML
    assert NFT_CSS.is_file()
    assert NFT_JS.is_file()


def test_trophies_page_defaults_to_nft_gallery():
    assert 'id="trophy-theme-nft"' in TROPHIES_HTML
    assert "trophy-theme-nft" in TROPHIES_HTML
    assert 'id="nft-gallery"' in TROPHIES_HTML
    assert 'data-tab="gallery"' in TROPHIES_HTML
    assert 'class="tab active" data-tab="gallery"' in TROPHIES_HTML or (
        'data-tab="gallery" class="tab active"' in TROPHIES_HTML
    )


def test_trophies_page_copy_is_nft_collection():
    lower = TROPHIES_HTML.lower()
    assert "nft" in lower
    assert "collectible" in lower or "collection" in lower
    assert 'id="trophy-modal-token"' in TROPHIES_HTML
    assert 'id="nft-ledger"' in TROPHIES_HTML


def test_trophies_page_keeps_ledger_and_filters():
    assert 'data-tab="unlocked"' in TROPHIES_HTML
    assert 'data-tab="locked"' in TROPHIES_HTML
    assert 'data-tab="ledger"' in TROPHIES_HTML
    assert 'id="trophies-data-table"' in TROPHIES_HTML
    assert 'id="trophy-tbody"' in TROPHIES_HTML
