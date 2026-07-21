"""P3 detail page upgrades — static verification (items 131–160)."""
import os


ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _read(*parts):
    path = os.path.join(ROOT, *parts)
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_p3_151_vin_table():
    js = _read("static", "js", "mn2-explorer-detail.js")
    py = _read("backend", "services", "mn2_explorer_data.py")
    assert "renderVins" in js
    assert "Inputs" in js
    assert "_normalize_vins" in py
    assert '"vin"' in py


def test_p3_152_fee_display():
    js = _read("static", "js", "mn2-explorer-detail.js")
    py = _read("backend", "services", "mn2_explorer_data.py")
    assert "Fee" in js and "row(" in js
    assert "_tx_fee_from_raw" in py
    assert '"fee"' in py


def test_p3_153_confirmation_progress_bar():
    js = _read("static", "js", "mn2-explorer-detail.js")
    css = _read("static", "css", "mn2-crypto-hub.css")
    assert "renderConfirmBar" in js
    assert "ex-confirm-bar" in css
    assert 'role="progressbar"' in js


def test_p3_154_qr_on_address_page():
    js = _read("static", "js", "mn2-explorer-detail.js")
    html = _read("explorer", "address.html")
    assert "renderAddressQr" in js
    assert "qrcode.min.js" in html


def test_p3_155_block_tx_table():
    js = _read("static", "js", "mn2-explorer-detail.js")
    assert "renderBlockTxTable" in js
    assert "/explorer/tx/" in js


def test_p3_156_breadcrumbs():
    js = _read("static", "js", "mn2-explorer-detail.js")
    for page in ("tx.html", "address.html", "block.html"):
        html = _read("explorer", page)
        assert 'id="ex-breadcrumb"' in html
    assert "setBreadcrumb" in js
    assert "Crypto Hub" in js


def test_p3_157_json_ld():
    js = _read("static", "js", "mn2-explorer-detail.js")
    assert "application/ld+json" in js
    assert "BreadcrumbList" in js
    assert "setSeoMeta" in js


def test_p3_158_open_graph_meta():
    js = _read("static", "js", "mn2-explorer-detail.js")
    for page in ("tx.html", "address.html", "block.html"):
        html = _read("explorer", page)
        assert 'property="og:title"' in html
        assert 'property="og:description"' in html
    assert "og:title" in js


def test_p3_159_raw_json_toggle():
    js = _read("static", "js", "mn2-explorer-detail.js")
    css = _read("static", "css", "mn2-crypto-hub.css")
    for page in ("tx.html", "address.html", "block.html"):
        html = _read("explorer", page)
        assert 'id="ex-raw-toggle"' in html
        assert 'id="ex-raw-json"' in html
    assert "bindRawToggle" in js
    assert "ex-raw-json" in css


def test_p3_160_embed_mode():
    js = _read("static", "js", "mn2-explorer-detail.js")
    css = _read("static", "css", "mn2-crypto-hub.css")
    assert "initEmbed" in js
    assert "embed" in js
    assert "ex-embed" in css


def test_p3_backend_normalize_vins_coinbase():
    from backend.services.mn2_explorer_data import _normalize_vins, _tx_fee_from_raw

    vins = _normalize_vins([{"n": 0, "coinbase": "abc", "sequence": 4294967295}])
    assert len(vins) == 1
    assert vins[0]["coinbase"] is True

    fee = _tx_fee_from_raw({
        "fee": -0.001,
        "vin": [{"txid": "a", "vout": 0, "value": 1.0}],
        "vout": [{"value": 0.999}],
    })
    assert fee == 0.001
