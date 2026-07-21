"""P7 future/backlog upgrades — verification (items 231–250)."""
import os
from unittest.mock import patch

import pytest


ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _staking_app():
    from flask import Flask
    from backend.routes.mn2_staking_routes import mn2_staking_bp

    app = Flask(__name__)
    app.register_blueprint(mn2_staking_bp)
    return app


def test_p7_231_mempool_visualizer():
    js = _read("static", "js", "mn2-explorer-p7.js")
    html = _read("explorer", "index.html")
    assert "ex-mempool-feed" in html
    assert "loadMempoolFeed" in js
    assert "/api/mn2/mempool" in js


def test_p7_232_block_reward():
    from backend.services import mn2_explorer_data

    detail_js = _read("static", "js", "mn2-explorer-detail.js")
    assert "block_reward" in detail_js
    with patch.object(mn2_explorer_data, "_fetch_block") as fb, patch(
        "backend.services.mn2_rpc_client.getblockhash",
        return_value={"result": "abc"},
    ), patch("backend.services.mn2_rpc_client._call") as call:
        fb.return_value = {
            "result": {
                "height": 1,
                "hash": "abc",
                "tx": ["cbtx"],
                "time": 1,
            }
        }
        call.return_value = {"result": {"vout": [{"value": 5.0}, {"value": 5.0}]}}
        blk = mn2_explorer_data.block_detail("1")
    assert blk["block_reward"] == 10.0


def test_p7_233_staking_calculator_widget():
    html = _read("explorer", "index.html")
    js = _read("static", "js", "mn2-explorer-p7.js")
    assert "ex-calc-amount" in html
    assert "/api/mn2/staking/calculator" in js


def test_p7_234_burn_tracker_deferred():
    doc = _read("docs", "EXPLORER_UPGRADES_250.md")
    assert "234" in doc
    assert "deferred" in doc.split("234")[1].split("|")[2].lower()


def test_p7_237_chain_sync_api():
    from backend.services import mn2_explorer_data

    with patch("backend.services.mn2_rpc_client.getblockchaininfo") as bi:
        bi.return_value = {
            "result": {
                "blocks": 100,
                "headers": 100,
                "verificationprogress": 1.0,
            }
        }
        sync = mn2_explorer_data.chain_sync_status()
    assert sync["synced"] is True
    r = _staking_app().test_client().get("/api/mn2/explorer/chain-sync")
    assert r.status_code == 200


def test_p7_238_fork_detection():
    from backend.services import mn2_explorer_data

    sync = {"blocks": 100, "headers": 110, "headers_behind": 10}
    fork = mn2_explorer_data.fork_status(sync)
    assert fork["fork_risk"] is True
    r = _staking_app().test_client().get("/api/mn2/explorer/fork-status")
    assert r.status_code == 200


def test_p7_239_price_history_api():
    from backend.services import mn2_explorer_data

    with patch("backend.services.mn2_network_stats.get_history") as gh:
        gh.return_value = [{"ts": "t", "mn2_usd_price": 0.01}]
        data = mn2_explorer_data.price_history_30d()
    assert data["count"] == 1
    js = _read("static", "js", "mn2-explorer-p7.js")
    assert "loadPriceChart" in js


def test_p7_242_pool_vs_network_chart():
    js = _read("static", "js", "mn2-explorer-p7.js")
    assert "loadStakeChart" in js
    assert "pool_total_staked" in js


def test_p7_243_order_book_widget():
    js = _read("static", "js", "mn2-explorer-p7.js")
    html = _read("explorer", "index.html")
    assert "ex-ob-ticker" in html
    assert "/api/market/ticker" in js


def test_p7_244_discord_embed_api():
    from backend.services import mn2_explorer_data

    with patch.object(mn2_explorer_data, "block_detail") as bd:
        bd.return_value = {
            "height": 42,
            "hash": "abc",
            "tx_count": 3,
            "block_reward": 10.0,
            "difficulty": 1.5,
        }
        payload = mn2_explorer_data.discord_block_embed("42", base_url="https://example.test")
    assert payload["embeds"][0]["title"] == "MN2 Block #42"
    with patch("backend.services.mn2_explorer_data.block_detail") as bd:
        bd.return_value = {
            "height": 42,
            "hash": "abc",
            "tx_count": 3,
            "block_reward": 10.0,
            "difficulty": 1.5,
        }
        r = _staking_app().test_client().get("/api/mn2/explorer/discord-embed?block=42")
    assert r.status_code == 200
    assert "embeds" in r.get_json()


def test_p7_245_mobile_deep_links():
    js = _read("static", "js", "mn2-explorer-detail.js")
    assert "setMobileDeepLink" in js
    assert "masternoder://" in js


def test_p7_246_address_validation_js():
    js = _read("static", "js", "mn2-address-validate.js")
    html = _read("explorer", "index.html")
    assert "Mn2AddressValidate" in js
    assert "mn2-address-validate.js" in html


def test_p7_250_status_page():
    assert os.path.isfile(os.path.join(ROOT, "explorer", "status.html"))
    routes = _read("backend", "routes", "all_page_routes.py")
    assert "/explorer/status" in routes
    js = _read("static", "js", "mn2-explorer-status.js")
    assert "/api/mn2/explorer/status" in js


def test_p7_mempool_sample_txids():
    from backend.services import mn2_explorer_data

    with patch("backend.services.mn2_rpc_client.getmempoolinfo") as mi, patch(
        "backend.services.mn2_rpc_client._call"
    ) as call:
        mi.return_value = {"result": {"size": 2, "bytes": 100}}
        call.return_value = {"result": ["a" * 64, "b" * 64]}
        stats = mn2_explorer_data.mempool_stats()
    assert stats["sample_txids"] == ["a" * 64, "b" * 64]


def test_p7_explorer_status_includes_fork_sync():
    from backend.services import mn2_explorer_data

    with patch("backend.services.mn2_rpc_client.getblockcount", return_value={"result": 1}), patch.object(
        mn2_explorer_data, "rich_list", return_value=[{"address": "x", "balance": 1}]
    ), patch.object(mn2_explorer_data, "mempool_stats", return_value={"size": 0}), patch.object(
        mn2_explorer_data, "chain_sync_status", return_value={"synced": True}
    ), patch.object(
        mn2_explorer_data, "fork_status", return_value={"fork_risk": False}
    ):
        status = mn2_explorer_data.explorer_status()
    assert "chain_sync" in status["checks"]
    assert "fork" in status["checks"]
