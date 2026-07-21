"""P6 documentation upgrades — verification (items 211–230)."""
import os


ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def test_p6_215_architecture_diagram():
    doc = _read("docs", "EXPLORER_ARCHITECTURE.md")
    assert "mermaid" in doc
    assert "eiquidus" in doc.lower() or "Eqi" in doc


def test_p6_216_sequence_diagram():
    doc = _read("docs", "EXPLORER_ARCHITECTURE.md")
    assert "sequenceDiagram" in doc
    assert "classify_search" in doc or "classify" in doc


def test_p6_217_runbook_index_stuck():
    doc = _read("docs", "EXPLORER_RUNBOOKS.md")
    assert "index stuck" in doc.lower() or "index_synced" in doc


def test_p6_218_runbook_chainz_fallback():
    doc = _read("docs", "EXPLORER_RUNBOOKS.md")
    assert "Chainz" in doc
    assert "MN2_EXPLORER_KIND" in doc


def test_p6_219_faq_em_dash():
    doc = _read("docs", "EXPLORER_FAQ.md")
    assert "—" in doc or "em dash" in doc.lower()
    assert "price" in doc.lower()


def test_p6_220_faq_rich_list():
    doc = _read("docs", "EXPLORER_FAQ.md")
    assert "rich list" in doc.lower()


def test_p6_221_changelog():
    doc = _read("docs", "CHANGELOG_EXPLORER.md")
    assert "2026" in doc
    assert "PR" in doc or "Added" in doc


def test_p6_223_jsdoc_overview():
    js = _read("static", "js", "mn2-explorer-overview.js")
    assert "/**" in js
    assert "initUrlSearch" in js


def test_p6_224_openapi_docs_route():
    from flask import Flask
    from backend.routes.mn2_staking_routes import mn2_staking_bp

    app = Flask(__name__)
    app.register_blueprint(mn2_staking_bp)
    c = app.test_client()
    r = c.get("/api/docs/explorer")
    assert r.status_code == 200
    assert b"swagger" in r.data.lower()
    r2 = c.get("/api/docs", headers={"Accept": "application/json"})
    assert r2.status_code == 200
    body = r2.get_json()
    assert any(d.get("id") == "explorer" for d in body.get("docs", []))


def test_p6_225_contributor_guide():
    doc = _read("docs", "EXPLORER_CONTRIBUTING.md")
    assert "ex-tile" in doc
    assert "mn2-explorer-overview.js" in doc


def test_p6_229_profile_hub_link():
    js = _read("static", "js", "profile-mn2-wallet.js")
    assert "hub_address_url" in js
    assert "Crypto Hub" in js


def test_p6_230_shop_hub_link():
    html = _read("shop", "index.html")
    assert "shop_revenue_hub_url" in html or "hub_address_url" in html
    assert "Crypto Hub" in html


def test_p6_hub_url_helpers():
    from backend.services.mn2_explorer_urls import hub_address_url, hub_search_url, hub_tx_url

    addr = "JNKzUoRpc7nhnPKZkzxJe4Vkmaz82o8jiX"
    assert hub_address_url(addr) == f"/explorer/address/{addr}"
    assert "q=" in hub_search_url(addr)
    txid = "a" * 64
    assert hub_tx_url(txid) == f"/explorer/tx/{txid}"
