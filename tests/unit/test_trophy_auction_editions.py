"""Plan 001 T-U1 — edition-aware auction house listings."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _edition(item_id: str = "top25-01", edition_no: int = 3, *, held: bool = False, listed: str | None = None):
    hold_until = None
    if held:
        hold_until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
    row = {
        "item_id": item_id,
        "item_name": "Genesis Node Sigil",
        "edition_no": edition_no,
        "edition_key": f"TRO-{item_id}-{edition_no}",
        "acquired_via": "paypal",
        "hold_until": hold_until,
    }
    if listed:
        row["listed_listing_id"] = listed
    return row


def test_list_edition_buy_transfers_metadata():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb
    from backend.services import trophy_fulfillment_service as tfs

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"success": True, "points": {"coins": 500}}
    mock_points.add_points.return_value = {"success": True}

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                with patch("backend.services.trophy_fulfillment_service.is_trophy_item", return_value=True):
                    assert shopdb.add_to_inventory("seller", "top25-01", "Genesis", 1)
                    tfs._append_edition_record("seller", _edition(edition_no=3))

                    listing = auction.create_listing("seller", "top25-01", 1, 150, edition_no=3)
                    assert listing["edition_no"] == 3
                    assert listing["edition_key"] == "TRO-top25-01-3"

                    seller_editions = tfs.get_trophy_editions("seller", "top25-01")
                    assert seller_editions[0]["listed_listing_id"] == listing["listing_id"]

                    with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                        result = auction.buy_listing("buyer", listing["listing_id"])

                    assert result["listing"]["status"] == "sold"
                    assert result["edition_no"] == 3
                    buyer_editions = tfs.get_trophy_editions("buyer", "top25-01")
                    assert len(buyer_editions) == 1
                    assert buyer_editions[0]["edition_no"] == 3
                    assert buyer_editions[0].get("listed_listing_id") is None
                    assert buyer_editions[0].get("transfer_history")
                    assert tfs.get_trophy_editions("seller", "top25-01") == []
                    buyer_inv = shopdb.get_inventory("buyer")
                    assert buyer_inv and buyer_inv[0]["item_id"] == "top25-01"
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_trophy_listing_requires_explicit_edition_no():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                with patch("backend.services.trophy_fulfillment_service.is_trophy_item", return_value=True):
                    assert shopdb.add_to_inventory("seller", "top25-01", "Genesis", 1)
                    try:
                        auction.create_listing("seller", "top25-01", 1, 100)
                        raised = False
                    except auction.AuctionError as ex:
                        raised = True
                        assert "edition_no" in str(ex).lower()
                    assert raised
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_paypal_held_edition_cannot_be_listed():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb
    from backend.services import trophy_fulfillment_service as tfs

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                with patch("backend.services.trophy_fulfillment_service.is_trophy_item", return_value=True):
                    assert shopdb.add_to_inventory("seller", "top25-01", "Genesis", 1)
                    tfs._append_edition_record("seller", _edition(edition_no=1, held=True))
                    try:
                        auction.create_listing("seller", "top25-01", 1, 100, edition_no=1)
                        raised = False
                    except auction.AuctionError as ex:
                        raised = True
                        assert "hold" in str(ex).lower()
                    assert raised
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_cancel_listing_releases_edition():
    from backend.services import shop_auction_service as auction
    from backend.services import shop_db_service as shopdb
    from backend.services import trophy_fulfillment_service as tfs

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                with patch("backend.services.trophy_fulfillment_service.is_trophy_item", return_value=True):
                    assert shopdb.add_to_inventory("seller", "top25-01", "Genesis", 1)
                    tfs._append_edition_record("seller", _edition(edition_no=2))
                    listing = auction.create_listing("seller", "top25-01", 1, 120, edition_no=2)
                    cancelled = auction.cancel_listing("seller", listing["listing_id"])
                    assert cancelled["status"] == "cancelled"
                    edition = tfs.get_edition("seller", "top25-01", 2)
                    assert edition is not None
                    assert edition.get("listed_listing_id") is None
                    assert shopdb.get_inventory("seller")[0]["quantity"] == 1
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_auction_list_route_accepts_edition_no():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)

    listing = {"listing_id": "abc", "edition_no": 3, "edition_key": "TRO-top25-01-3", "status": "active"}
    with app.test_client() as client:
        with patch("backend.routes.shop_routes._resolve_user_id", return_value="seller"):
            with patch("backend.services.shop_auction_service.create_listing", return_value=listing) as mock_create:
                resp = client.post(
                    "/api/shop/auction/list",
                    json={"item_id": "top25-01", "quantity": 1, "price_coins": 150, "edition_no": 3},
                )
                mock_create.assert_called_once_with("seller", "top25-01", 1, 150, edition_no=3)

    assert resp.status_code == 200
    body = resp.get_json() or {}
    assert body["success"] is True
    assert body["listing"]["edition_no"] == 3
