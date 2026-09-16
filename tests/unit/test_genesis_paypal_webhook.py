"""Genesis auto-backfill worker + PayPal trophy dispute webhook clawback."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_genesis_prewarm_starts_before_milestone():
    from backend.services import block_mint_service as bms

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "manifest.json")
        config = os.path.join(tmp, "config.json")
        with open(config, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "enabled": True,
                    "lookback_blocks": 5,
                    "milestone_block": 1_000_000,
                    "genesis_block": 1,
                    "backfill_from_genesis_at_milestone": True,
                    "backfill_batch_size": 10,
                    "genesis_prewarm_within_blocks": 5000,
                    "milestone_discord_announced": True,
                },
                f,
            )
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            with patch.object(bms, "_CONFIG_PATH", config):
                with patch.object(bms, "_current_block_height", return_value=996_000):
                    with patch("backend.services.block_trophy_media_service.ensure_block_media"):
                        sync = bms.sync_block_height()
                        assert sync["success"] is True
                        assert sync.get("genesis_backfill") is True
                        assert len(sync["added"]) == 50


def test_run_genesis_backfill_batches():
    from backend.services import block_mint_service as bms

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "manifest.json")
        config = os.path.join(tmp, "config.json")
        with open(config, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "enabled": True,
                    "milestone_block": 1_000_000,
                    "genesis_block": 1,
                    "backfill_from_genesis_at_milestone": True,
                    "backfill_batch_size": 5,
                    "milestone_discord_announced": True,
                },
                f,
            )
        heights = [1_000_000, 1_000_004, 1_000_008]
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            with patch.object(bms, "_CONFIG_PATH", config):
                with patch.object(bms, "_current_block_height", side_effect=heights):
                    with patch("backend.services.block_trophy_media_service.ensure_block_media"):
                        result = bms.run_genesis_backfill_batches(max_batches=3)
        assert result["success"] is True
        assert result["batches_run"] >= 1
        assert result["blocks_added"] >= 5


def test_paypal_webhook_claws_back_trophy():
    from backend.services import trophy_paypal_webhook_service as tpw
    from backend.services import trophy_fulfillment_service as tfs

    with tempfile.TemporaryDirectory() as tmp:
        captures = os.path.join(tmp, "captures.json")
        editions = os.path.join(tmp, "editions")
        os.makedirs(editions, exist_ok=True)
        uid = "buyer_claw"
        with open(os.path.join(editions, f"{uid}.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "editions": [
                        {
                            "item_id": "top25-01",
                            "edition_no": 1,
                            "edition_key": "TRO-top25-01-1",
                            "paypal_capture_id": "CAP-DISPUTE-1",
                        }
                    ]
                },
                f,
            )
        ref = tfs.payment_ref_for_capture("CAP-DISPUTE-1", "top25-01")
        with open(captures, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "captures": {
                        ref: {
                            "user_id": uid,
                            "item_id": "top25-01",
                            "edition_no": 1,
                            "edition_key": "TRO-top25-01-1",
                            "edition": {"paypal_capture_id": "CAP-DISPUTE-1"},
                        }
                    }
                },
                f,
            )
        events = os.path.join(tmp, "events.jsonl")
        with patch.object(tfs, "_CAPTURES_PATH", captures):
            with patch.object(tpw, "_EVENTS_PATH", events):
                    with patch("backend.services.trophy_paypal_clawback_service.clawback_trophy_edition") as claw:
                        claw.return_value = {"success": True, "edition_key": "TRO-top25-01-1"}
                        body = {
                            "id": "WH-DISPUTE-1",
                            "event_type": "CUSTOMER.DISPUTE.CREATED",
                            "resource": {"id": "CAP-DISPUTE-1"},
                        }
                        out, status = tpw.process_trophy_paypal_webhook(body)
                        assert status == 200
                        assert out.get("handled") == "trophy_clawback"
                        claw.assert_called_once()

                        dup, dup_status = tpw.process_trophy_paypal_webhook(body)
                        assert dup_status == 200
                        assert dup.get("duplicate") is True


def test_release_block_claim_for_edition():
    from backend.services import block_mint_service as bms

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "manifest.json")
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "drops": {
                        "42": {
                            "height": 42,
                            "claimed_by": "alice",
                            "edition_key": "TRO-block-42-1",
                        }
                    }
                },
                f,
            )
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            result = bms.release_block_claim_for_edition(
                "block-42",
                edition_key="TRO-block-42-1",
                user_id="alice",
            )
            assert result["success"] is True
            doc = bms._read_json(manifest, {})
            assert doc["drops"]["42"]["claimed_by"] is None
