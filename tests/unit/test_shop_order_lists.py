"""Shop purchases + stall listing APIs used by the two-list account view."""
from __future__ import annotations

import json
from unittest.mock import patch

from flask import Flask

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _shop_app():
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)
    return app


def test_taxonomy_status_buckets_include_stall():
    from backend.services.shop_taxonomy_service import order_status_bucket

    assert order_status_bucket("pending_payment") == "pending"
    assert order_status_bucket("active") == "pending"
    assert order_status_bucket("sold") == "completed"
    assert order_status_bucket("bought") == "completed"
    assert order_status_bucket("paid") == "completed"
    assert order_status_bucket("refunded") == "refunded"
    assert order_status_bucket("expired") == "cancelled"


def test_shop_purchases_api_is_catalog_only(monkeypatch):
    """GET /api/shop/purchases must not dump masternode hosting JSON."""
    app = _shop_app()

    def fake_purchases(user_id, limit=50):
        return [
            {
                "id": 1,
                "item_id": "booster-1",
                "item_name": "Booster Pack #1",
                "quantity": 2,
                "price_type": "coins",
                "price_paid_coins": 40,
                "purchase_status": "completed",
                "created_at": "2026-09-01T12:00:00Z",
            }
        ]

    monkeypatch.setattr("backend.services.shop_db_service.get_purchases", fake_purchases)
    with app.test_client() as client:
        r = client.get("/api/shop/purchases?user_id=alice&limit=20")
    assert r.status_code == 200
    body = r.get_json() or {}
    assert body.get("success") is True
    rows = body.get("purchases") or []
    assert len(rows) == 1
    assert rows[0]["item_id"] == "booster-1"
    assert rows[0].get("status_bucket") == "completed"
    assert rows[0].get("subcategory") == "boosts"
    assert "private_key" not in json.dumps(rows)


def test_stall_orders_api_returns_listing_rows(monkeypatch):
    app = _shop_app()
    monkeypatch.setattr(
        "backend.services.shop_auction_service.list_user_listings",
        lambda user_id, limit=100: {
            "selling": [
                {
                    "listing_id": "L-active",
                    "item_id": "theme-dark",
                    "item_name": "Dark Theme",
                    "quantity": 1,
                    "price_coins": 25,
                    "status": "active",
                    "created_at": "2026-09-02T00:00:00Z",
                }
            ],
            "bought": [],
            "sold": [
                {
                    "listing_id": "L-sold",
                    "item_id": "booster-1",
                    "item_name": "Booster Pack #1",
                    "quantity": 1,
                    "price_coins": 80,
                    "status": "sold",
                    "sold_at": "2026-09-03T00:00:00Z",
                    "created_at": "2026-09-01T00:00:00Z",
                }
            ],
        },
    )
    with app.test_client() as client:
        r = client.get("/api/shop/stall-orders?user_id=alice")
    assert r.status_code == 200
    body = r.get_json() or {}
    assert body.get("success") is True
    rows = body.get("listings") or []
    ids = {row.get("listing_id") for row in rows}
    assert ids == {"L-active", "L-sold"}
    active = next(row for row in rows if row["listing_id"] == "L-active")
    assert active.get("source") == "listing"
    assert active.get("status_bucket") == "pending"
    assert active.get("subcategory") == "look"
    sold = next(row for row in rows if row["listing_id"] == "L-sold")
    assert sold.get("status_bucket") == "completed"


def test_build_user_order_lists_keeps_sources_separate(monkeypatch):
    from backend.services.shop_order_list_service import build_user_order_lists

    monkeypatch.setattr(
        "backend.services.shop_db_service.get_purchases",
        lambda user_id, limit=50: [
            {
                "id": 9,
                "item_id": "theme-dark",
                "item_name": "Dark Theme",
                "quantity": 1,
                "price_type": "coins",
                "price_paid_coins": 10,
                "purchase_status": "completed",
                "created_at": "2026-09-01T00:00:00Z",
                "category": "themes",
            }
        ],
    )
    monkeypatch.setattr(
        "backend.services.shop_auction_service.list_user_listings",
        lambda user_id, limit=100: {
            "selling": [
                {
                    "listing_id": "L1",
                    "item_id": "booster-1",
                    "item_name": "Booster Pack #1",
                    "quantity": 1,
                    "price_coins": 40,
                    "status": "active",
                    "created_at": "2026-09-02T00:00:00Z",
                }
            ],
            "bought": [],
            "sold": [],
        },
    )
    out = build_user_order_lists("alice", limit=20)
    assert out["counts"]["shop"] == 1
    assert out["counts"]["stall"] == 1
    assert out["purchases"][0]["source"] == "purchase"
    assert out["listings"][0]["source"] == "listing"
    blob = json.dumps(out)
    assert "private_key" not in blob
    assert "wif" not in blob
