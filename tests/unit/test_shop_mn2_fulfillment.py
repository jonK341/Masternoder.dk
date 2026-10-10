"""MN2 pack purchase auto-delivery (shop coins, PayPal, item effects)."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from flask import Flask

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


@pytest.fixture
def points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})
    return db


def test_fulfill_mn2_pack_credits_balance(points_db):
    from backend.services.shop_mn2_fulfillment_service import fulfill_mn2_purchase

    out = fulfill_mn2_purchase(
        "buyer1",
        "mn2-pack-s",
        1,
        source="test",
        reference="test-ref-1",
    )
    assert out["success"] is True
    assert out["mn2_granted"] == 1.0
    bal = points_db.get_all_points("buyer1")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(1.0, rel=1e-6)


def test_fulfill_mn2_pack_idempotent_reference(points_db):
    from backend.services.shop_mn2_fulfillment_service import fulfill_mn2_purchase

    r1 = fulfill_mn2_purchase("buyer1", "mn2-pack-m", 1, source="test", reference="dup-ref")
    r2 = fulfill_mn2_purchase("buyer1", "mn2-pack-m", 1, source="test", reference="dup-ref")
    assert r1["success"] is True
    assert r2.get("duplicate") is True
    bal = points_db.get_all_points("buyer1")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(5.0, rel=1e-6)


def test_apply_shop_item_effects_credits_mn2_pack(points_db):
    from backend.routes.shop_routes import _apply_shop_item_effects

    item = {
        "id": "mn2-pack-l",
        "name": "20 MN2",
        "mn2_granted": 20,
        "price": 2000,
    }
    _apply_shop_item_effects("u_shop", "mn2-pack-l", item, 1, purchase_ref="purchase-99")
    bal = points_db.get_all_points("u_shop")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(20.0, rel=1e-6)


def test_paypal_capture_credits_mn2_pack(points_db, monkeypatch):
    from backend.routes.paypal_routes import paypal_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(paypal_bp)

    with app.test_client() as client:
        with patch("backend.services.paypal_service.capture_order", return_value={
            "success": True, "order_id": "order-mn2", "capture_id": "cap-mn2", "amount": "4.99", "currency": "USD",
        }), patch("backend.routes.shop_routes.get_coin_pack_map", return_value={}), patch(
            "backend.routes.shop_routes.get_mn2_pack_map",
            return_value={"mn2-pack-m": {"id": "mn2-pack-m", "name": "5 MN2", "mn2_granted": 5, "price_usd": 4.99}},
        ), patch("backend.routes.shop_routes._get_paypal_shop_items", return_value={}):
            response = client.post(
                "/api/paypal/capture",
                json={"order_id": "order-mn2", "item_id": "mn2-pack-m", "user_id": "u_pp"},
            )

    body = response.get_json() or {}
    assert response.status_code == 200
    assert body["success"] is True
    assert body.get("mn2_granted") == 5.0
    bal = points_db.get_all_points("u_pp")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(5.0, rel=1e-6)


def test_mn2_packs_api_lists_config():
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)
    with app.test_client() as client:
        response = client.get("/api/shop/mn2-packs")
    assert response.status_code == 200
    data = response.get_json() or {}
    assert data.get("success") is True
    ids = [p.get("id") for p in data.get("mn2_packs") or []]
    assert "mn2-pack-s" in ids
    assert "mn2-pack-m" in ids
