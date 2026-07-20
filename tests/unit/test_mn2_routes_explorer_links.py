"""Explorer URL cutover tests for mn2 routes and network-overview."""
from flask import Flask


def _staking_app():
    from backend.routes.mn2_staking_routes import mn2_staking_bp
    app = Flask(__name__)
    app.register_blueprint(mn2_staking_bp)
    return app


def test_network_overview_explorer_fields_iquidus(monkeypatch):
    monkeypatch.setenv("MN2_EXPLORER_BASE_URL", "https://selfhosted.example/")
    monkeypatch.setenv("MN2_EXPLORER_KIND", "iquidus")
    monkeypatch.setattr(
        "backend.services.mn2_chainz.network_overview",
        lambda: {"block_height": 1, "source": {}},
    )
    monkeypatch.setattr("backend.services.mn2_staking_service.total_staked", lambda: 0)
    monkeypatch.setattr("backend.services.mn2_staking_service.dynamic_apr", lambda: 0)

    c = _staking_app().test_client()
    r = c.get("/api/mn2/network-overview")
    assert r.status_code == 200
    data = r.get_json()
    assert data["explorer_kind"] == "iquidus"
    assert data["explorer_base_url"] == "https://selfhosted.example/"


def test_explorer_tx_url_shapes():
    from backend.services.mn2_explorer_urls import explorer_tx_url

    chainz = {"explorer_base_url": "https://chainz.cryptoid.info/mn2/", "explorer_kind": "chainz"}
    iquidus = {"explorer_base_url": "https://selfhosted.example/", "explorer_kind": "iquidus"}
    txid = "a" * 64
    assert "tx.dws?txid=" in explorer_tx_url(txid, chainz)
    assert explorer_tx_url(txid, iquidus) == f"https://selfhosted.example/tx/{txid}"


def test_explorer_address_api(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.address_detail",
        lambda addr: {"address": addr, "balance": 1.5, "source": "iquidus"},
    )
    monkeypatch.setattr(
        "backend.services.mn2_explorer_urls.explorer_address_url",
        lambda addr, cfg=None: f"https://selfhosted.example/address/{addr}",
    )
    c = _staking_app().test_client()
    r = c.get("/api/mn2/explorer/address/JTestAddress1234567890123456789012")
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] is True
    assert body["address"]["balance"] == 1.5


def test_rich_list_api(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.rich_list",
        lambda limit=100: [{"rank": 1, "address": "Jx", "balance": 100}],
    )
    c = _staking_app().test_client()
    r = c.get("/api/mn2/rich-list?limit=5")
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] is True
    assert body["count"] == 1


def test_explorer_search_api(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.classify_search",
        lambda q: {"type": "tx", "txid": "a" * 64, "path": "/explorer/tx/" + ("a" * 64)},
    )
    c = _staking_app().test_client()
    r = c.get("/api/mn2/explorer/search?q=" + ("a" * 64))
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] is True
    assert body["type"] == "tx"


def test_explorer_block_api(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.block_detail",
        lambda ref: {"height": 100, "hash": "abc", "source": "rpc"},
    )
    monkeypatch.setattr(
        "backend.services.mn2_explorer_urls.explorer_block_url",
        lambda ref, cfg=None: f"https://selfhosted.example/block/{ref}",
    )
    c = _staking_app().test_client()
    r = c.get("/api/mn2/explorer/block/100")
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] is True
    assert body["block"]["height"] == 100


def test_mempool_api(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.mempool_stats",
        lambda: {"size": 3, "bytes": 1200, "source": "rpc"},
    )
    c = _staking_app().test_client()
    r = c.get("/api/mn2/mempool")
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] is True
    assert body["size"] == 3
