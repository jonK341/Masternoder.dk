"""Platform upgrade batch — Exchange, Casino, Shop route smoke tests."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from flask import Flask

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(*blueprints):
    app = Flask(__name__)
    app.config["TESTING"] = True
    for bp in blueprints:
        app.register_blueprint(bp)
    return app


def test_exchange_profit_pair_search_ui_route():
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    app = _app(crypto_exchange_bp)
    with app.test_client() as client:
        with patch(
            "backend.services.exchange_profit_pair_search_service.ui_payload",
            return_value={"success": True, "enabled": True, "tiles": [], "hot_symbols": ["BTC"]},
        ):
            r = client.get("/api/exchange/profit-pair-search?limit=5")
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        assert data["hot_symbols"] == ["BTC"]


def test_exchange_treasury_stash_polished():
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    app = _app(crypto_exchange_bp)
    with app.test_client() as client:
        with patch(
            "backend.services.exchange_treasury_service.treasury_status",
            return_value={
                "success": True,
                "ledger_stashed_usd": 100.0,
                "ledger_stashed_usd_paper": 60.0,
                "ledger_stashed_usd_live": 40.0,
                "live_stash_usd": 40.0,
                "ledger_entries": 3,
                "treasury_user_id": "platform_treasury",
                "mn2_balance": 10.0,
                "coins": 0,
                "stash_quote": "MN2",
                "auto_stash_on_trade": True,
                "enabled": True,
                "exchange_assets": {},
            },
        ), patch(
            "backend.services.exchange_treasury_service.treasury_monitor_snapshot",
            return_value={"success": True, "ledger_stashed_usd": 100.0},
        ):
            r = client.get("/api/exchange/treasury/stash")
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        assert data["total_stash_usd"] == 100.0
        assert "monitor" in data
        assert "recent_stashes" in data


def test_exchange_monitor_metrics_passthrough():
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    app = _app(crypto_exchange_bp)
    with app.test_client() as client:
        with patch(
            "backend.services.exchange_trading_monitor_service.live_monitor",
            return_value={"success": True, "feed": [], "totals": {}},
        ), patch(
            "backend.services.profit_daemon_ops_service.daemon_metrics_snapshot",
            return_value={"success": True, "profit_kill": False, "hot_symbols": ["DOGE"]},
        ):
            r = client.get("/api/exchange/monitor/live?include_metrics=1")
        assert r.status_code == 200
        data = r.get_json()
        assert data["daemon_metrics"]["hot_symbols"] == ["DOGE"]

        with patch(
            "backend.services.profit_daemon_ops_service.daemon_metrics_snapshot",
            return_value={"success": True, "mode": "paper"},
        ), patch(
            "backend.services.exchange_treasury_service.treasury_monitor_snapshot",
            return_value={"ledger_stashed_usd": 1.0},
        ):
            r2 = client.get("/api/exchange/monitor/metrics")
        assert r2.status_code == 200
        assert r2.get_json().get("treasury_snapshot") == {"ledger_stashed_usd": 1.0}


def test_casino_agent_tick_summary_route():
    from backend.routes.casino_routes import casino_bp

    app = _app(casino_bp)
    with app.test_client() as client:
        with patch(
            "backend.services.casino_agents_service.tick_summary",
            return_value={"success": True, "total_ticks": 5, "wins": 3, "losses": 2},
        ):
            r = client.get("/api/casino/agents/tick-summary?hours=12")
        assert r.status_code == 200
        assert r.get_json()["total_ticks"] == 5


def test_casino_rg_status_alias():
    from backend.routes.casino_routes import casino_bp

    app = _app(casino_bp)
    with app.test_client() as client:
        with patch(
            "backend.services.casino_responsible_gaming.status_for_user",
            return_value={"success": True, "enabled": True, "session_loss": 0},
        ):
            r = client.get("/api/casino/rg/status?user_id=u1&currency=coins")
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        assert data["endpoint"] == "/api/casino/rg/status"


def test_shop_catalog_filter_params():
    from backend.routes.shop_routes import shop_bp

    app = _app(shop_bp)
    sample = [
        {"id": "a", "name": "Alpha Theme", "category": "themes", "price": 100, "tags": ["dark"]},
        {"id": "b", "name": "MN2 Pack", "category": "mn2_crypto", "price": 500, "mn2_granted": 5,
         "payment_rails": ["paypal", "mn2"]},
    ]
    with app.test_client() as client:
        with patch("backend.routes.shop_routes._get_shop_items", return_value=sample):
            r = client.get("/api/shop/items?category=themes")
        assert r.status_code == 200
        data = r.get_json()
        assert data["count"] == 1
        assert data["items"][0]["id"] == "a"

        with patch("backend.routes.shop_routes._get_shop_items", return_value=sample):
            r2 = client.get("/api/shop/items?mn2_only=1")
        assert r2.get_json()["count"] == 1
        assert r2.get_json()["items"][0]["id"] == "b"


def test_shop_mn2_fulfillment_status_route():
    from backend.routes.shop_routes import shop_bp

    app = _app(shop_bp)
    with app.test_client() as client:
        with patch(
            "backend.services.shop_mn2_fulfillment_service.fulfillment_status_for_user",
            return_value={"success": True, "user_id": "u1", "mn2_balance": 5.0, "status": "ok"},
        ):
            r = client.get("/api/shop/mn2/fulfillment/status?user_id=u1")
        assert r.status_code == 200
        assert r.get_json()["mn2_balance"] == 5.0


def test_profit_pair_search_ui_payload_disabled():
    from backend.services import exchange_profit_pair_search_service as pps

    with patch.object(pps, "enabled", return_value=False), patch.object(
        pps, "read_index", return_value={"hits": [], "updated_at": "2026-01-01T00:00:00Z"},
    ):
        out = pps.ui_payload(refresh=False, limit=5)
    assert out["success"] is True
    assert out["enabled"] is False
    assert out["tiles"] == []
