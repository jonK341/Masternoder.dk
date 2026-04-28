"""
Shop purchase → inventory / purchases API flow (user_id-scoped, same as shop + profile UIs).

Proves: POST /api/game/shop/purchase with user_id + coin balance can succeed, and
GET /api/shop/inventory + GET /api/shop/purchases see rows when shop DB helpers succeed.

When real SQLite migrations are absent, shop_db_service no-ops; tests mock DB layer.
Run: pytest tests/unit/test_shop_purchase_profile_flow.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _minimal_shop_app():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)
    return app


def _first_coin_priced_item_id(client):
    r = client.get("/api/game/shop/items")
    assert r.status_code == 200
    data = r.get_json() or {}
    items = data.get("items") or []
    for it in items:
        p = it.get("price")
        if isinstance(p, int) and p > 0:
            return it["id"], int(p)
    return None, None


@pytest.mark.slow
def test_shop_purchase_fails_without_balance():
    """Insufficient coins → 400 (unified_points mocked; no real DB)."""
    mock_db = MagicMock()
    mock_db.get_all_points.return_value = {"success": True, "points": {"coins": 0}}
    app = _minimal_shop_app()
    with app.test_client() as client:
        iid, price = _first_coin_priced_item_id(client)
        if not iid:
            return
        uid = "api_flow_user_insufficient"
        with patch("backend.services.unified_points_database.unified_points_db", mock_db):
            r = client.post(
                "/api/shop-v3/purchase",
                json={"user_id": uid, "item_id": iid, "quantity": 1},
            )
        assert r.status_code == 400
        body = r.get_json() or {}
        assert body.get("success") is False


@pytest.mark.slow
def test_shop_purchase_and_profile_inventory_apis_with_mocks():
    """
    With coins + mocked shop DB: purchase succeeds; inventory + purchases APIs return the item.
    Mirrors how the shop page passes user_id and loads /api/shop/inventory.
    """
    app = _minimal_shop_app()
    inv_by_user: dict[str, list] = {}
    purchases_by_user: dict[str, list] = {}

    def fake_fulfill_shop_purchase(**kwargs):
        uid = kwargs.get("user_id")
        row = {
            "id": 4242,
            "item_id": kwargs.get("item_id"),
            "item_name": kwargs.get("item_name"),
            "quantity": kwargs.get("quantity", 1),
            "price_type": kwargs.get("price_type"),
            "price_paid_coins": kwargs.get("price_paid_coins"),
        }
        purchases_by_user.setdefault(uid, []).append(row)
        inv_by_user.setdefault(uid, []).append({
            "item_id": kwargs.get("item_id"),
            "item_name": kwargs.get("item_name"),
            "quantity": kwargs.get("quantity", 1),
            "is_active": True,
            "created_at": "2026-01-01T00:00:00+00:00",
        })
        return 4242

    def fake_get_inventory(user_id):
        return list(inv_by_user.get(user_id, []))

    def fake_get_purchases(user_id, limit=50):
        return list(purchases_by_user.get(user_id, []))[:limit]

    mock_db = MagicMock()
    mock_db.get_all_points.return_value = {"success": True, "points": {"coins": 500_000}}
    mock_db.add_points.return_value = {"success": True}

    with app.test_client() as client:
        iid, price = _first_coin_priced_item_id(client)
        if not iid:
            return
        uid = "api_flow_user_ok"

        with patch("backend.services.unified_points_database.unified_points_db", mock_db):
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=True):
                with patch("backend.services.shop_db_service.fulfill_shop_purchase", side_effect=fake_fulfill_shop_purchase):
                    pr = client.post(
                        "/api/game/shop/purchase",
                        json={"user_id": uid, "item_id": iid, "quantity": 1},
                    )
                    assert pr.status_code == 200, pr.get_data(as_text=True)
                    prj = pr.get_json()
                    assert prj.get("success") is True
                    assert prj.get("purchase_id") == 4242

        with patch("backend.services.shop_db_service.shop_tables_exist", return_value=True):
            with patch("backend.services.shop_db_service.get_inventory", side_effect=fake_get_inventory):
                ir = client.get(f"/api/shop/inventory?user_id={uid}")
                assert ir.status_code == 200
                inv = (ir.get_json() or {}).get("inventory") or []
                assert any((row.get("item_id") == iid) for row in inv)

            with patch("backend.services.shop_db_service.get_purchases", side_effect=fake_get_purchases):
                pr2 = client.get(f"/api/shop/purchases?user_id={uid}")
                assert pr2.status_code == 200
                pur = (pr2.get_json() or {}).get("purchases") or []
                assert any((row.get("item_id") == iid) for row in pur)
