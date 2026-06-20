from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_fixed_price_listing_reserves_inventory_and_cancel_restores():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("seller", "item-a", "Item A", 2)

                listing = auction.create_listing("seller", "item-a", 1, 123)
                assert listing["status"] == "active"
                assert listing["price_coins"] == 123
                assert shopdb.get_inventory("seller")[0]["quantity"] == 1

                cancelled = auction.cancel_listing("seller", listing["listing_id"])
                assert cancelled["status"] == "cancelled"
                assert shopdb.get_inventory("seller")[0]["quantity"] == 2
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_buy_listing_moves_item_and_pays_seller_minus_fee():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"success": True, "points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("seller", "item-a", "Item A", 1)
                listing = auction.create_listing("seller", "item-a", 1, 100)

                with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                    result = auction.buy_listing("buyer", listing["listing_id"])

                assert result["listing"]["status"] == "sold"
                assert result["fee_coins"] == 5
                assert result["seller_payout_coins"] == 95
                assert shopdb.get_inventory("seller") == []
                buyer_inv = shopdb.get_inventory("buyer")
                assert buyer_inv and buyer_inv[0]["item_id"] == "item-a"
                assert mock_points.add_points.call_args_list[0].kwargs["user_id"] == "buyer"
                assert mock_points.add_points.call_args_list[0].kwargs["amount"] == -100
                assert mock_points.add_points.call_args_list[1].kwargs["user_id"] == "seller"
                assert mock_points.add_points.call_args_list[1].kwargs["amount"] == 95
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_buy_listing_can_use_mn2_balance():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"success": True, "points": {"mn2_balance": 2.0}}
    mock_points.add_points.return_value = {"success": True}

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("seller", "item-mn2", "MN2 Item", 1)
                listing = auction.create_listing("seller", "item-mn2", 1, 100)

                with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                    result = auction.buy_listing("buyer", listing["listing_id"], payment_method="mn2")

                assert result["listing"]["status"] == "sold"
                assert result["payment_method"] == "mn2"
                assert result["price_mn2"] == 1.0
                assert mock_points.add_points.call_args_list[0].kwargs["point_type"] == "mn2_balance"
                assert mock_points.add_points.call_args_list[0].kwargs["amount"] == -1.0
                assert mock_points.add_points.call_args_list[1].kwargs["user_id"] == "seller"
                assert mock_points.add_points.call_args_list[1].kwargs["amount"] == 0.95
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_bid_flow_accepts_highest_offer_and_records_history():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"success": True, "points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("seller", "item-bid", "Bid Item", 1)
                listing = auction.create_listing("seller", "item-bid", 1, 200)
                with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                    bid_result = auction.place_bid("buyer", listing["listing_id"], 150)
                assert bid_result["listing"]["highest_bid_coins"] == 150
                assert bid_result["bid"]["escrowed"] is True
                assert bid_result["escrow_coins"] == 150

                with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                    sale = auction.accept_bid("seller", listing["listing_id"], bid_result["bid"]["bid_id"])

                assert sale["listing"]["status"] == "sold"
                assert sale["price_coins"] == 150
                debits = [c.kwargs.get("amount") for c in mock_points.add_points.call_args_list if c.kwargs.get("amount", 0) < 0]
                assert -150 in debits
                assert -150 not in debits[1:] if len(debits) > 1 else True
                history = auction.price_history("item-bid")
                assert history and history[0]["price_coins"] == 150
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_bid_escrow_released_on_outbid():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"success": True, "points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("seller", "item-out", "Out Item", 1)
                listing = auction.create_listing("seller", "item-out", 1, 100)
                with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                    auction.place_bid("buyer_a", listing["listing_id"], 120)
                    auction.place_bid("buyer_b", listing["listing_id"], 150)
                sources = [c.kwargs.get("source") for c in mock_points.add_points.call_args_list]
                assert "marketplace_bid_escrow" in sources
                assert "marketplace_bid_escrow_release" in sources
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_cancel_listing_releases_bid_escrow():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"success": True, "points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("seller", "item-cancel", "Cancel Item", 1)
                listing = auction.create_listing("seller", "item-cancel", 1, 80)
                with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                    auction.place_bid("buyer", listing["listing_id"], 90)
                    auction.cancel_listing("seller", listing["listing_id"])
                sources = [c.kwargs.get("source") for c in mock_points.add_points.call_args_list]
                assert "marketplace_bid_escrow_release" in sources
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_auction_routes_are_registered_and_return_lists():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)

    with app.test_client() as client:
        with patch("backend.services.shop_auction_service.list_active_listings", return_value=[]):
            response = client.get("/api/shop/auction/listings")

    assert response.status_code == 200
    data = response.get_json() or {}
    assert data["success"] is True
    assert data["listings"] == []


def test_auction_read_routes_degrade_to_empty_lists_on_service_failure():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)

    with app.test_client() as client:
        with patch("backend.services.shop_auction_service.list_active_listings", side_effect=RuntimeError("storage down")):
            listings = client.get("/api/shop/auction/listings")
        with patch("backend.services.shop_auction_service.list_user_listings", side_effect=RuntimeError("storage down")):
            mine = client.get("/api/shop/auction/my-listings?user_id=user-a")
        with patch("backend.services.shop_auction_service.price_history", side_effect=RuntimeError("storage down")):
            history = client.get("/api/shop/auction/price-history")

    assert listings.status_code == 200
    listings_body = listings.get_json() or {}
    assert listings_body["success"] is True
    assert listings_body["listings"] == []
    assert listings_body["count"] == 0
    assert "warning" in listings_body

    assert mine.status_code == 200
    mine_body = mine.get_json() or {}
    assert mine_body["success"] is True
    assert mine_body["selling"] == []
    assert mine_body["bought"] == []
    assert mine_body["sold"] == []

    assert history.status_code == 200
    history_body = history.get_json() or {}
    assert history_body["success"] is True
    assert history_body["history"] == []
