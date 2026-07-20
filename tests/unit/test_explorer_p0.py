"""P0 critical explorer upgrades — automated verification (items 1–30)."""
import re

from flask import Flask


def _staking_app():
    from backend.routes.mn2_staking_routes import mn2_staking_bp
    from backend.routes.mn2_masternode_routes import mn2_masternode_bp
    app = Flask(__name__)
    app.register_blueprint(mn2_staking_bp)
    app.register_blueprint(mn2_masternode_bp)
    return app


def _page_app():
    from backend.routes.all_page_routes import all_page_bp
    app = Flask(__name__)
    app.register_blueprint(all_page_bp)
    return app


# P0-1: mn2_masternode blueprint registered (services route exists)
def test_p0_01_services_route_registered():
    c = _staking_app().test_client()
    r = c.get("/api/mn2/services")
    assert r.status_code == 200
    body = r.get_json()
    assert isinstance(body.get("services"), list)


# P0-2: centralized explorer URL builders
def test_p0_02_centralized_explorer_urls():
    from backend.services.mn2_explorer_urls import explorer_tx_url, explorer_address_url, explorer_block_url
    cfg = {"explorer_base_url": "https://selfhosted.example/", "explorer_kind": "iquidus"}
    txid = "a" * 64
    assert explorer_tx_url(txid, cfg).endswith("/tx/" + txid)
    assert explorer_address_url("JAddr", cfg).endswith("/address/JAddr")
    assert explorer_block_url("100", cfg).endswith("/block/100")


# P0-3: config keys present
def test_p0_03_explorer_config_keys():
    from backend.services.mn2_explorer_urls import load_explorer_config
    cfg = load_explorer_config()
    for key in ("explorer_base_url", "explorer_kind", "explorer_local_api_url", "explorer_fallback_base_url"):
        assert key in cfg


# P0-4: hub HTML does not default ex-open to /explorer/ self-loop
def test_p0_04_ex_open_not_self_loop():
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "..", "explorer", "index.html")
    with open(path, encoding="utf-8") as f:
        html = f.read()
    assert 'id="ex-open" href="/explorer/"' not in html
    assert 'id="ex-open"' in html


# P0-5/P0-29: ACTIVE counts as enabled
def test_p0_05_active_masternode_counts_as_enabled():
    from backend.services.mn2_explorer_data import is_masternode_active, masternodes

    assert is_masternode_active("ACTIVE")
    assert is_masternode_active("ENABLED")
    assert not is_masternode_active("MISSING")


# P0-7: zero price filtered in chainz ticker
def test_p0_07_zero_price_filtered(monkeypatch):
    from backend.services import mn2_chainz
    monkeypatch.setattr(mn2_chainz, "chainz_ticker_usd_with_updated", lambda: {"price": 0.0, "last_updated_iso": "x"})
    assert mn2_chainz.chainz_ticker_usd() is None


# P0-8/P0-9: shared overview payload includes explorer fields
def test_p0_08_overview_payload_has_explorer_fields(monkeypatch):
    monkeypatch.setenv("MN2_EXPLORER_BASE_URL", "https://selfhosted.example/")
    monkeypatch.setenv("MN2_EXPLORER_KIND", "iquidus")
    monkeypatch.setattr("backend.services.mn2_chainz.network_overview", lambda: {"source": {}})
    monkeypatch.setattr("backend.services.mn2_staking_service.total_staked", lambda: 0)
    monkeypatch.setattr("backend.services.mn2_staking_service.dynamic_apr", lambda: 0)
    c = _staking_app().test_client()
    r = c.get("/api/mn2/network-overview")
    data = r.get_json()
    assert data["explorer_kind"] == "iquidus"
    assert data["explorer_base_url"] == "https://selfhosted.example/"


# P0-10: rich list API returns success shape
def test_p0_10_rich_list_api(monkeypatch):
    monkeypatch.setattr("backend.services.mn2_explorer_data.rich_list", lambda limit=100: [])
    c = _staking_app().test_client()
    r = c.get("/api/mn2/rich-list?limit=5")
    assert r.status_code == 200
    assert r.get_json()["success"] is True


# P0-11–13: in-page HTML routes
def test_p0_11_13_detail_page_routes():
    c = _page_app().test_client()
    txid = "b" * 64
    assert c.get("/explorer/tx/" + txid).status_code == 200
    assert c.get("/explorer/address/JTestAddress1234567890123456789012").status_code == 200
    assert c.get("/explorer/block/12345").status_code == 200


# P0-14: tx API
def test_p0_14_tx_api(monkeypatch):
    txid = "c" * 64
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.tx_detail",
        lambda t: {"txid": t, "confirmations": 1, "source": "rpc"},
    )
    monkeypatch.setattr("backend.services.mn2_explorer_urls.explorer_tx_url", lambda t, cfg=None: "/tx/" + t)
    r = _staking_app().test_client().get("/api/mn2/explorer/tx/" + txid)
    assert r.status_code == 200
    assert r.get_json()["transaction"]["txid"] == txid


# P0-15: address API
def test_p0_15_address_api(monkeypatch):
    addr = "JNKzUoRpc7nhnPKZkzxJe4Vkmaz82o8jiX"
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.address_detail",
        lambda a: {"address": a, "balance": 1.0, "source": "iquidus"},
    )
    monkeypatch.setattr("backend.services.mn2_explorer_urls.explorer_address_url", lambda a, cfg=None: "/addr/" + a)
    r = _staking_app().test_client().get("/api/mn2/explorer/address/" + addr)
    assert r.status_code == 200


# P0-16: block API
def test_p0_16_block_api(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.block_detail",
        lambda ref: {"height": 1, "hash": "h", "source": "rpc"},
    )
    monkeypatch.setattr("backend.services.mn2_explorer_urls.explorer_block_url", lambda ref, cfg=None: "/block/" + ref)
    r = _staking_app().test_client().get("/api/mn2/explorer/block/1")
    assert r.status_code == 200


# P0-17–18: rich-list + supply-stats
def test_p0_17_18_supply_and_rich(monkeypatch):
    monkeypatch.setattr("backend.services.mn2_explorer_data.rich_list", lambda limit=100: [{"rank": 1}])
    monkeypatch.setattr("backend.services.mn2_explorer_data.supply_stats", lambda: {"circulating_supply": 1.0, "source": {}})
    c = _staking_app().test_client()
    assert c.get("/api/mn2/rich-list").status_code == 200
    assert c.get("/api/mn2/supply-stats").status_code == 200


# P0-19: search classifier
def test_p0_19_search_classifier():
    from backend.services.mn2_explorer_data import classify_search
    txid = "d" * 64
    assert classify_search(txid)["type"] == "tx"
    assert classify_search("999")["type"] == "block"


# P0-20: mempool API
def test_p0_20_mempool_api(monkeypatch):
    monkeypatch.setattr("backend.services.mn2_explorer_data.mempool_stats", lambda: {"size": 2, "source": "rpc"})
    r = _staking_app().test_client().get("/api/mn2/mempool")
    assert r.status_code == 200
    assert r.get_json()["size"] == 2


# P0-21–25: hub JS markers
def test_p0_21_25_hub_js_features():
    import os
    js_path = os.path.join(os.path.dirname(__file__), "..", "..", "static", "js", "mn2-explorer-overview.js")
    with open(js_path, encoding="utf-8") as f:
        js = f.read()
    assert "/api/mn2/explorer/search" in js
    assert "ex-refresh" in js or "refreshAll" in js
    assert "inPageBlockLink" in js
    assert "circulatingSupply" in js


# P0-26–28: detail JS features
def test_p0_26_28_detail_js_features():
    import os
    js_path = os.path.join(os.path.dirname(__file__), "..", "..", "static", "js", "mn2-explorer-detail.js")
    with open(js_path, encoding="utf-8") as f:
        js = f.read()
    assert "ex-copy-btn" in js
    assert "renderVouts" in js
    assert "renderBlock" in js


# P0-30: ETag on network-overview
def test_p0_30_etag_on_overview(monkeypatch):
    monkeypatch.setattr("backend.services.mn2_chainz.network_overview", lambda: {"source": {}})
    monkeypatch.setattr("backend.services.mn2_staking_service.total_staked", lambda: 0)
    monkeypatch.setattr("backend.services.mn2_staking_service.dynamic_apr", lambda: 0)
    c = _staking_app().test_client()
    r = c.get("/api/mn2/network-overview")
    assert r.headers.get("ETag", "").startswith('W/"')
    assert "max-age=30" in r.headers.get("Cache-Control", "")


# P0-2b: mn2_routes uses centralized URLs (no duplicate _explorer_* helpers)
def test_p0_02b_no_duplicate_explorer_helpers_in_mn2_routes():
    import os
    path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "routes", "mn2_routes.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "def _explorer_" not in src
    assert "from backend.services.mn2_explorer_urls import" in src
