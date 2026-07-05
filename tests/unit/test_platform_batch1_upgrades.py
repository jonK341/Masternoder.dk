"""Platform batch-1 remaining upgrades — service and route tests."""
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


def test_batch1_widgets_exchange():
    from backend.services.platform_batch1_service import get_batch1_widgets

    with patch(
        "backend.services.platform_upgrades_batch2_service.get_batch2_widgets",
        return_value={"success": True, "area": "exchange"},
    ), patch(
        "backend.services.platform_batch2_extras_service.enrich_area_widgets",
        side_effect=lambda area, w, user_id=None: {**w, "batch2_extras": {
            "liquidity_heatmap": {"binance": 0.8},
            "remaining": {},
        }},
    ):
        out = get_batch1_widgets("exchange", user_id="u1")
    assert out.get("success") is not False
    b1 = out.get("batch1") or {}
    assert 19 in (b1.get("upgrade_ids") or [])
    assert b1.get("agent_marketplace_link", {}).get("href")


def test_batch1_widgets_shop():
    from backend.services.platform_batch1_service import get_batch1_widgets

    with patch(
        "backend.services.platform_upgrades_batch2_service.get_batch2_widgets",
        return_value={"success": True},
    ), patch(
        "backend.services.platform_batch2_extras_service.enrich_area_widgets",
        side_effect=lambda area, w, user_id=None: {**w, "batch2_extras": {
            "auction_href": "/shop?tab=auction",
            "flash_sale_ends_at": "2026-07-06T00:00:00Z",
            "flash_sale_active": True,
            "remaining": {"shop_analytics": {"catalog_size": 42}},
        }},
    ), patch(
        "backend.services.platform_batch1_service._vip_tier",
        return_value={"tier": "gold", "label": "VIP Gold"},
    ):
        out = get_batch1_widgets("shop", user_id="u1")
    b1 = out.get("batch1") or {}
    assert b1.get("vip_tier_badge", {}).get("tier") == "gold"
    assert b1.get("shop_analytics", {}).get("catalog_size") == 42


def test_batch1_route():
    from backend.routes.platform_upgrades_routes import platform_upgrades_bp

    app = _app(platform_upgrades_bp)
    with app.test_client() as client:
        with patch(
            "backend.services.platform_batch1_service.get_batch1_widgets",
            return_value={"success": True, "area": "casino", "batch1": {"upgrade_ids": [48]}},
        ):
            r = client.get("/api/platform/batch1/casino/widgets?user_id=u1")
        assert r.status_code == 200
        assert r.get_json().get("batch1", {}).get("upgrade_ids") == [48]


def test_roadmap_all_done():
    from backend.services.platform_upgrades_service import get_roadmap

    data = get_roadmap()
    assert data.get("total") == 100
    assert data.get("planned") == 0
    assert data.get("done") == 100
