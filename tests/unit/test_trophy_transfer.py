"""Plan 001 T-U2 / U6 — peer trophy edition transfers."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _edition(edition_no: int = 1, *, held: bool = False, listed: str | None = None):
    hold_until = None
    if held:
        hold_until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
    row = {
        "item_id": "top25-01",
        "item_name": "Genesis Node Sigil",
        "edition_no": edition_no,
        "edition_key": f"TRO-top25-01-{edition_no}",
        "acquired_via": "paypal",
        "hold_until": hold_until,
    }
    if listed:
        row["listed_listing_id"] = listed
    return row


def test_happy_path_peer_transfer():
    from backend.services import shop_db_service as shopdb
    from backend.services import trophy_fulfillment_service as tfs
    from backend.services import trophy_transfer_service as tts

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("alice", "top25-01", "Genesis", 1)
                tfs._append_edition_record("alice", _edition(2))

                result = tts.transfer_trophy_edition("alice", "bob", "top25-01", 2)
                assert result["success"] is True
                assert tfs.get_trophy_editions("alice", "top25-01") == []
                bob_editions = tfs.get_trophy_editions("bob", "top25-01")
                assert len(bob_editions) == 1
                assert bob_editions[0]["edition_no"] == 2
                assert bob_editions[0]["acquired_via"] == "peer_transfer"
                assert bob_editions[0].get("transferred_from") == "alice"
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_guest_blocked():
    from backend.services import trophy_transfer_service as tts

    result = tts.transfer_trophy_edition("guest", "bob", "top25-01", 1)
    assert result["success"] is False
    assert result["error"] == "guest_blocked"


def test_transfer_listed_edition_fails():
    from backend.services import shop_db_service as shopdb
    from backend.services import trophy_fulfillment_service as tfs
    from backend.services import trophy_transfer_service as tts

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("alice", "top25-01", "Genesis", 1)
                tfs._append_edition_record("alice", _edition(1, listed="listing-abc"))

                result = tts.transfer_trophy_edition("alice", "bob", "top25-01", 1)
                assert result["success"] is False
                assert result["error"] == "edition_already_listed"
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_transfer_paypal_held_fails():
    from backend.services import shop_db_service as shopdb
    from backend.services import trophy_fulfillment_service as tfs
    from backend.services import trophy_transfer_service as tts

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        try:
            with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                assert shopdb.add_to_inventory("alice", "top25-01", "Genesis", 1)
                tfs._append_edition_record("alice", _edition(1, held=True))

                result = tts.transfer_trophy_edition("alice", "bob", "top25-01", 1)
                assert result["success"] is False
                assert result["error"] == "edition_paypal_held"
        finally:
            os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_transfer_route():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)

    with app.test_client() as client:
        with patch("backend.routes.shop_routes._resolve_user_id", return_value="alice"):
            with patch(
                "backend.services.trophy_transfer_service.transfer_trophy_edition",
                return_value={"success": True, "edition_no": 2},
            ) as mock_xfer:
                resp = client.post(
                    "/api/shop/trophies/transfer",
                    json={
                        "recipient_id": "bob",
                        "item_id": "top25-01",
                        "edition_no": 2,
                    },
                )
                mock_xfer.assert_called_once_with("alice", "bob", "top25-01", 2, note=None)

    assert resp.status_code == 200
    assert (resp.get_json() or {}).get("success") is True
