"""Plan 001 BM-U1–BM-U4 — block trophy drops and claim."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_sync_and_list_drops():
    from backend.services import block_mint_service as bms

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "block_mint_manifest.json")
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            with patch.object(bms, "_current_block_height", return_value=1005):
                sync = bms.sync_block_height()
                assert sync["success"] is True
                assert sync["block_height"] == 1005
                assert len(sync["added"]) >= 1

                drops = bms.get_block_drops(limit=3)
                assert drops["success"] is True
                assert len(drops["drops"]) >= 1
                assert drops["drops"][0]["series"] == "block_mint"
                assert drops["drops"][0]["id"].startswith("block-")


def test_claim_block_trophy_mn2():
    from backend.services import block_mint_service as bms
    from backend.services import trophy_fulfillment_service as tfs

    mock_points = MagicMock()
    mock_points.get_all_points.return_value = {"success": True, "points": {"mn2_balance": 10.0}}
    mock_points.add_points.return_value = {"success": True}

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "block_mint_manifest.json")
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "drops": {
                        "1000": {
                            "height": 1000,
                            "item_id": "block-1000",
                            "detected_at": "2026-01-01T00:00:00Z",
                            "claimed_by": None,
                        }
                    },
                    "last_height": 1000,
                },
                f,
            )
        counters = os.path.join(tmp, "trophy_edition_counters.json")
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            with patch.object(tfs, "_EDITION_COUNTERS_PATH", counters):
                with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                    with patch("backend.services.trophy_pricing_service.get_effective_price") as mock_price:
                        mock_price.return_value = {
                            "success": True,
                            "effective_price_coins": 299,
                            "effective_price_usd": 2.99,
                        }
                        with patch("backend.services.shop_db_service.shop_tables_exist", return_value=False):
                            os.environ["MASTERNODER_LOG_DIR"] = tmp
                            try:
                                uid = "block_claim_test_user"
                                result = bms.claim_block_trophy(uid, 1000, payment_method="mn2")
                                assert result["success"] is True
                                assert result.get("edition_no") is not None
                                editions = tfs.get_trophy_editions(uid, "block-1000")
                                assert len(editions) == 1
                                assert editions[0]["edition_no"] == result["edition_no"]
                                assert editions[0]["acquired_via"] == "block_mint"
                            finally:
                                os.environ.pop("MASTERNODER_LOG_DIR", None)


def test_block_mint_drops_route():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)

    payload = {"success": True, "drops": [{"id": "block-1"}], "block_height": 1}
    with app.test_client() as client:
        with patch("backend.services.block_mint_service.get_block_drops", return_value=payload):
            resp = client.get("/api/shop/block-mint/drops?limit=5")

    assert resp.status_code == 200
    assert (resp.get_json() or {}).get("success") is True
