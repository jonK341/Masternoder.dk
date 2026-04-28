from __future__ import annotations

import tempfile
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_mn2_balance_purchase_refunds_when_fulfillment_fails():
    from backend.services.shop_mn2_purchase_core import purchase_with_mn2_balance

    mock_points = MagicMock()
    mock_points.get_all_points.side_effect = [
        {"success": True, "points": {"mn2_balance": 5.0}},
        {"success": True, "points": {"mn2_balance": 4.0}},
    ]
    mock_points.add_points.return_value = {"success": True}

    with patch("backend.routes.shop_routes._get_shop_items", return_value=[{"id": "item-a", "name": "Item A", "price": 100}]), \
         patch("backend.services.unified_points_database.unified_points_db", mock_points), \
         patch("backend.services.shop_db_service.fulfill_shop_purchase", side_effect=RuntimeError("inventory unavailable")), \
         patch("backend.services.mn2_ledger.append_entry") as append_entry:
        body, status = purchase_with_mn2_balance("user-a", "item-a", 1)

    assert status == 500
    assert body["success"] is False
    assert body["refund_applied"] is True
    assert mock_points.add_points.call_args_list[0].kwargs["amount"] == -1.0
    assert mock_points.add_points.call_args_list[1].kwargs["amount"] == 1.0
    append_entry.assert_called_once()
    assert append_entry.call_args.kwargs["entry_type"] == "shop_refund"


def test_coin_purchase_refunds_when_fulfillment_fails():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)

    mock_points = MagicMock()
    mock_points.get_all_points.side_effect = [
        {"success": True, "points": {"coins": 500}},
        {"success": True, "points": {"coins": 400}},
    ]
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        with patch("backend.routes.shop_routes._get_shop_items", return_value=[{"id": "item-a", "name": "Item A", "price": 100}]), \
             patch("backend.services.unified_points_database.unified_points_db", mock_points), \
             patch("backend.services.shop_db_service.fulfill_shop_purchase", side_effect=RuntimeError("inventory unavailable")):
            response = client.post("/api/shop-v3/purchase", json={"user_id": "user-a", "item_id": "item-a"})

    body = response.get_json() or {}
    assert response.status_code == 500
    assert body["success"] is False
    assert "refunded" in body["error"]
    assert mock_points.add_points.call_args_list[0].kwargs["amount"] == -100
    assert mock_points.add_points.call_args_list[1].kwargs["amount"] == 100


def test_onchain_order_stays_pending_when_fulfillment_fails():
    from backend.services import mn2_order_payment_service as orders

    with tempfile.TemporaryDirectory() as tmp:
        original_data_dir = orders._data_dir
        orders._data_dir = lambda: tmp
        try:
            order = orders.create_order_payment("user-a", "item-a", "Item A", 1, 100, 1.0, "MxOrderAddr")

            with patch("backend.services.shop_db_service.fulfill_shop_purchase", side_effect=RuntimeError("db down")):
                result = orders.confirm_and_fulfill(order["payment_ref"], "tx123")

            assert result["status"] == "pending"
            assert result["txid"] == "tx123"
            assert "db down" in result["fulfillment_error"]
            assert orders.get_address_to_order_map()["MxOrderAddr"]["payment_ref"] == order["payment_ref"]
        finally:
            orders._data_dir = original_data_dir


def test_scanner_only_counts_orders_that_reach_fulfilled_status():
    from backend.services import mn2_deposit_scanner as scanner

    tx = {"category": "receive", "txid": "tx123", "address": "MxOrderAddr", "confirmations": 6, "amount": 1.0}
    order = {"payment_ref": "ref123", "amount_mn2": 1.0}

    with patch("backend.services.mn2_wallet_service.get_address_to_user_map", return_value={}), \
         patch("backend.services.mn2_rpc_client.listtransactions", return_value={"result": [tx]}), \
         patch("backend.services.mn2_ledger.is_txid_processed", return_value=False), \
         patch("backend.services.mn2_order_payment_service.get_address_to_order_map", return_value={"MxOrderAddr": order}), \
         patch("backend.services.mn2_order_payment_service.confirm_and_fulfill", return_value={"status": "pending"}):
        result = scanner.run_scanner()

    assert result["success"] is True
    assert result["orders_fulfilled"] == 0


def test_paypal_direct_item_applies_shop_effects_after_fulfillment():
    from flask import Flask
    from backend.routes.paypal_routes import paypal_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(paypal_bp)

    with app.test_client() as client:
        with patch("backend.services.paypal_service.capture_order", return_value={"success": True, "order_id": "order-1", "capture_id": "cap-1", "amount": 9.99, "currency": "USD"}), \
             patch("backend.routes.shop_routes.get_coin_pack_map", return_value={}), \
             patch("backend.routes.shop_routes._get_paypal_shop_items", return_value={"boost-a": {"name": "XP Booster 1h", "price_usd": 9.99}}), \
             patch("backend.services.shop_db_service.fulfill_shop_purchase", return_value=55), \
             patch("backend.routes.shop_routes._get_shop_items", return_value=[{"id": "boost-a", "name": "XP Booster 1h", "category": "boosts", "price": 100}]), \
             patch("backend.routes.shop_routes._apply_shop_item_effects") as apply_effects, \
             patch("backend.services.unified_points_database.unified_points_db", MagicMock()):
            response = client.post("/api/paypal/capture", json={"order_id": "order-1", "item_id": "boost-a", "user_id": "user-a"})

    assert response.status_code == 200
    body = response.get_json() or {}
    assert body["success"] is True
    assert body["item_granted"] == "boost-a"
    apply_effects.assert_called_once()
