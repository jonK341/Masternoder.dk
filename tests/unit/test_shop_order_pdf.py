"""PDF export of checked shop purchases and stall listings."""
from __future__ import annotations

from unittest.mock import patch

from flask import Flask

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


PURCHASES = [
    {
        "id": 9,
        "item_id": "booster-1",
        "item_name": "Booster Pack #1",
        "quantity": 2,
        "price_type": "coins",
        "price_paid_coins": 80,
        "purchase_status": "completed",
        "created_at": "2026-09-15T12:00:00+00:00",
    },
    {
        "id": 10,
        "item_id": "shop-super-stack-core",
        "item_name": "Super Stack Core",
        "quantity": 1,
        "price_type": "mn2",
        "price_paid_points": {"mn2": 1.25},
        "purchase_status": "completed",
        "created_at": "2026-09-14T12:00:00+00:00",
    },
]

LISTINGS = {
    "selling": [
        {
            "listing_id": "L-kit",
            "item_id": "dna-kit",
            "item_name": "DNA Test Kit",
            "quantity": 1,
            "price_coins": 55,
            "status": "active",
            "created_at": "2026-09-13T12:00:00+00:00",
        }
    ],
    "bought": [],
    "sold": [],
}


def _shop_app():
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)
    return app


def test_build_orders_pdf_contains_title_user_and_rows():
    from backend.services.shop_order_pdf_service import build_orders_pdf

    pdf = build_orders_pdf(
        user_id="alice",
        rows=[
            {
                "item_name": "Booster Pack #1",
                "quantity": 2,
                "price_type": "coins",
                "price_paid_coins": 80,
                "purchase_status": "completed",
                "created_at": "2026-09-15T12:00:00+00:00",
                "source": "purchase",
            }
        ],
        generated_at="2026-09-15 12:00 UTC",
    )
    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf
    assert b"Shop orders" in pdf
    assert b"User: alice" in pdf
    assert b"Booster Pack #1" in pdf
    assert b"80 coins" in pdf
    assert b"private_key" not in pdf
    assert b"wif" not in pdf


def test_order_pdf_empty_selection_returns_400():
    app = _shop_app()
    with app.test_client() as client:
        resp = client.post(
            "/api/shop/order-pdf",
            json={"user_id": "alice", "items": []},
        )
    assert resp.status_code == 400
    body = resp.get_json() or {}
    assert body.get("success") is False
    assert "select orders first" in str(body.get("error") or "").lower()


def test_order_pdf_missing_items_returns_400():
    app = _shop_app()
    with app.test_client() as client:
        resp = client.post("/api/shop/order-pdf", json={"user_id": "alice"})
    assert resp.status_code == 400
    body = resp.get_json() or {}
    assert "select orders first" in str(body.get("error") or "").lower()


def test_order_pdf_happy_path_with_fixture_purchases_and_listing():
    app = _shop_app()
    with app.test_client() as client:
        with patch("backend.services.shop_db_service.get_purchases", return_value=PURCHASES), patch(
            "backend.services.shop_auction_service.list_user_listings",
            return_value=LISTINGS,
        ):
            resp = client.post(
                "/api/shop/order-pdf",
                json={
                    "user_id": "alice",
                    "items": [
                        {"source": "purchase", "id": "9"},
                        {"source": "listing", "id": "L-kit"},
                    ],
                },
            )
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    data = resp.get_data()
    assert data.startswith(b"%PDF-1.4")
    assert b"Booster Pack #1" in data
    assert b"DNA Test Kit" in data
    assert b"User: alice" in data
    assert b"private_key" not in data
    assert "attachment" in (resp.headers.get("Content-Disposition") or "").lower()


def test_order_pdf_ignores_ids_that_are_not_this_users():
    app = _shop_app()
    with app.test_client() as client:
        with patch("backend.services.shop_db_service.get_purchases", return_value=PURCHASES), patch(
            "backend.services.shop_auction_service.list_user_listings",
            return_value=LISTINGS,
        ):
            resp = client.post(
                "/api/shop/order-pdf",
                json={
                    "user_id": "alice",
                    "items": [{"source": "purchase", "id": "9999"}],
                },
            )
    assert resp.status_code == 400
    body = resp.get_json() or {}
    assert "select orders first" in str(body.get("error") or "").lower()
