"""P1 explorer API upgrades — verification (items 71–80)."""
import gzip
import json

from flask import Flask


def _staking_app():
    from backend.routes.mn2_staking_routes import mn2_staking_bp
    app = Flask(__name__)
    app.register_blueprint(mn2_staking_bp)
    return app


def test_p1_71_block_previous_links(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.block_detail",
        lambda ref: {
            "height": 10,
            "hash": "abc",
            "previousblockhash": "prevhash",
            "txids": ["t" * 64],
            "source": "rpc",
        },
    )
    monkeypatch.setattr(
        "backend.services.mn2_explorer_urls.explorer_block_url",
        lambda ref, cfg=None: f"https://selfhosted.example/block/{ref}",
    )
    r = _staking_app().test_client().get("/api/mn2/explorer/block/10")
    body = r.get_json()
    assert body["block"]["previous_block_path"] == "/explorer/block/prevhash"
    assert "prevhash" in body["block"]["explorer_previous_block_url"]


def test_p1_72_address_txs_paginated(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.address_transactions",
        lambda addr, limit=25, offset=0: {
            "address": addr,
            "transactions": [{"txid": "a" * 64}],
            "count": 1,
            "limit": limit,
            "offset": offset,
            "source": "iquidus",
        },
    )
    addr = "JNKzUoRpc7nhnPKZkzxJe4Vkmaz82o8jiX"
    r = _staking_app().test_client().get(f"/api/mn2/explorer/address/{addr}/txs?limit=10&offset=0")
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] is True
    assert body["count"] == 1


def test_p1_73_explorer_status(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_explorer_data.explorer_status",
        lambda: {"status": "healthy", "explorer_kind": "iquidus", "checks": {}},
    )
    r = _staking_app().test_client().get("/api/mn2/explorer/status")
    assert r.status_code == 200
    assert r.get_json()["status"] == "healthy"
    assert "stale-while-revalidate" in r.headers.get("Cache-Control", "")


def test_p1_76_search_rate_limit(monkeypatch):
    monkeypatch.setattr("backend.routes.mn2_staking_routes._search_rate_ok", lambda: False)
    r = _staking_app().test_client().get("/api/mn2/explorer/search?q=123")
    assert r.status_code == 429


def test_p1_78_overview_stale_while_revalidate(monkeypatch):
    monkeypatch.setattr("backend.services.mn2_chainz.network_overview", lambda: {"source": {}})
    monkeypatch.setattr("backend.services.mn2_staking_service.total_staked", lambda: 0)
    monkeypatch.setattr("backend.services.mn2_staking_service.dynamic_apr", lambda: 0)
    r = _staking_app().test_client().get("/api/mn2/network-overview")
    assert "stale-while-revalidate=60" in r.headers.get("Cache-Control", "")


def test_p1_79_network_history_gzip(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_network_stats.get_history",
        lambda hours=24, limit=500: [{"block_height": i, "mn2_usd_price": 1.0} for i in range(200)],
    )
    r = _staking_app().test_client().get(
        "/api/mn2/network-history",
        headers={"Accept-Encoding": "gzip"},
    )
    assert r.status_code == 200
    assert r.headers.get("Content-Encoding") == "gzip"
    data = json.loads(gzip.decompress(r.data))
    assert data["success"] is True
    assert data["count"] == 200


def test_p1_80_openapi_spec():
    r = _staking_app().test_client().get("/api/mn2/explorer/openapi.json")
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("openapi", "").startswith("3.")
    assert "/api/mn2/explorer/status" in body.get("paths", {})
