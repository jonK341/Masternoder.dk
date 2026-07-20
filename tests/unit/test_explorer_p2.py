"""P2 hub UI upgrades — static verification (items 81–130)."""
import os
import re


ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _read(*parts):
    path = os.path.join(ROOT, *parts)
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_p2_116_skeleton_loaders():
    css = _read("static", "css", "mn2-crypto-hub.css")
    js = _read("static", "js", "mn2-explorer-overview.js")
    assert "ex-shimmer" in css
    assert "is-loading" in js
    assert "setLoading" in js


def test_p2_117_toast_on_errors():
    js = _read("static", "js", "mn2-explorer-overview.js")
    html = _read("explorer", "index.html")
    assert "function toast" in js
    assert 'id="ex-toast"' in html
    assert "rate_limit" in js or "rate limit" in js


def test_p2_118_keyboard_focus_search():
    js = _read("static", "js", "mn2-explorer-overview.js")
    assert "initKeyboard" in js
    assert "e.key !== '/'" in js or "e.key !== \"/\"" in js


def test_p2_119_tab_deeplink():
    js = _read("static", "js", "mn2-crypto-hub.js")
    assert "URLSearchParams" in js
    assert "tab" in js


def test_p2_120_export_csv():
    js = _read("static", "js", "mn2-explorer-overview.js")
    html = _read("explorer", "index.html")
    assert "exportHistoryCsv" in js
    assert 'id="ex-export-csv"' in html


def test_p2_121_print_styles():
    css = _read("static", "css", "mn2-crypto-hub.css")
    assert "@media print" in css


def test_p2_123_high_contrast_toggle():
    js = _read("static", "js", "mn2-explorer-overview.js")
    css = _read("static", "css", "mn2-crypto-hub.css")
    assert "ex-high-contrast" in js
    assert "ex-high-contrast" in css


def test_p2_124_reduced_motion():
    css = _read("static", "css", "mn2-crypto-hub.css")
    js = _read("static", "js", "mn2-explorer-overview.js")
    assert "prefers-reduced-motion" in css
    assert "reducedMotion" in js


def test_p2_126_share_button():
    js = _read("static", "js", "mn2-explorer-overview.js")
    assert "shareExplorer" in js


def test_p2_127_qr_for_address():
    js = _read("static", "js", "mn2-explorer-overview.js")
    html = _read("explorer", "index.html")
    assert "showAddressQr" in js
    assert 'id="ex-qr-modal"' in html


def test_p2_129_bookmarks_localstorage():
    js = _read("static", "js", "mn2-explorer-overview.js")
    assert "mn2_explorer_bookmarks" in js
    assert "toggleBookmark" in js


def test_p2_130_chart_palette_toggle():
    js = _read("static", "js", "mn2-explorer-overview.js")
    css = _read("static", "css", "mn2-crypto-hub.css")
    assert "ex-chart-alt" in js
    assert "ex-chart-alt" in css
    assert "chartColor" in js
