"""Plan 001 P-U1 — dynamic trophy pricing engine."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _catalog_item(item_id: str = "top25-01", base_usd: float = 2.10):
    return {
        "id": item_id,
        "name": "Genesis Node Sigil",
        "price": 210,
        "price_usd": base_usd,
        "tags": ["top25", "series_top25"],
        "category": "top25",
    }


def test_zero_sales_effective_equals_base():
    from backend.services.trophy_pricing_service import get_effective_price

    with patch("backend.services.trophy_pricing_service._catalog_item", return_value=_catalog_item()):
        with patch("backend.services.trophy_pricing_service._sales_7d", return_value=0):
            with patch("backend.services.trophy_pricing_service._auction_listing_count", return_value=0):
                with patch("backend.services.trophy_pricing_service._global_owner_count", return_value=0):
                    out = get_effective_price("top25-01")

    assert out["success"] is True
    assert abs(out["effective_price_usd"] - out["base_price_usd"]) < 0.01
    assert out["price_factors"]["demand_multiplier"] == 1.0
    assert out["price_factors"]["popularity_factor"] == 1.0


def test_sales_spike_increases_price_capped_at_ceiling():
    from backend.services import trophy_pricing_service as tps

    cfg = {
        "defaults": {
            "baseline_weekly": 5,
            "max_boost": 0.5,
            "pop_cap": 0.0,
            "pop_weight": 0.0,
            "floor_multiplier": 1.0,
            "ceiling_multiplier": 1.2,
        },
        "items": {"top25-01": {"ceiling_price_usd": 2.50}},
    }

    with patch.object(tps, "_catalog_item", return_value=_catalog_item(base_usd=2.10)):
        with patch.object(tps, "_load_config", return_value=cfg):
            with patch.object(tps, "_sales_7d", return_value=50):
                with patch.object(tps, "_auction_listing_count", return_value=0):
                    with patch.object(tps, "_global_owner_count", return_value=0):
                        out = tps.get_effective_price("top25-01")

    assert out["success"] is True
    assert out["effective_price_usd"] == 2.50
    assert out["price_factors"]["demand_multiplier"] > 1.0


def test_floor_prevents_effective_below_minimum():
    from backend.services import trophy_pricing_service as tps

    cfg = {
        "defaults": {"baseline_weekly": 5, "max_boost": 0.0, "pop_cap": 0.0, "pop_weight": 0.0},
        "items": {"top25-01": {"floor_price_usd": 3.00, "ceiling_price_usd": 9.00}},
    }

    with patch.object(tps, "_catalog_item", return_value=_catalog_item(base_usd=2.10)):
        with patch.object(tps, "_load_config", return_value=cfg):
            with patch.object(tps, "_sales_7d", return_value=0):
                with patch.object(tps, "_auction_listing_count", return_value=0):
                    with patch.object(tps, "_global_owner_count", return_value=0):
                        out = tps.get_effective_price("top25-01")

    assert out["success"] is True
    assert out["effective_price_usd"] == 3.00


def test_unknown_item_returns_not_found():
    from backend.services.trophy_pricing_service import get_effective_price

    with patch("backend.services.trophy_pricing_service._catalog_item", return_value=None):
        out = get_effective_price("missing-trophy")

    assert out["success"] is False
    assert out["error"] == "trophy_not_found"


def test_sales_7d_counts_file_mode_purchases(tmp_path, monkeypatch):
    from backend.services import trophy_pricing_service as tps
    from backend.services import shop_db_service as shopdb

    inv_root = tmp_path / "shop_file_mode"
    (inv_root / "purchases").mkdir(parents=True)
    recent = datetime.now(timezone.utc).isoformat()
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    purchase_doc = {
        "purchases": [
            {"item_id": "top25-01", "quantity": 2, "purchase_status": "completed", "created_at": recent},
            {"item_id": "top25-01", "quantity": 1, "purchase_status": "completed", "created_at": old},
            {"item_id": "top25-02", "quantity": 5, "purchase_status": "completed", "created_at": recent},
        ]
    }
    with open(inv_root / "purchases" / "buyer-a.json", "w", encoding="utf-8") as f:
        json.dump(purchase_doc, f)

    monkeypatch.setattr(shopdb, "_shop_file_root", lambda: str(inv_root))
    with patch.object(shopdb, "shop_tables_exist", return_value=False):
        assert tps._sales_7d("top25-01") == 2
