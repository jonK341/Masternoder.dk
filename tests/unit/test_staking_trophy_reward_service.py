"""Staking interval winners receive block trophy grants in wallet v2."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_pick_winners_and_skip_duplicate_interval():
    from backend.services import staking_trophy_reward_service as strs

    rows = [
        {"user_id": "alice", "reward_mn2": 0.5},
        {"user_id": "bob", "reward_mn2": 0.01},
        {"user_id": "", "reward_mn2": 1.0},
    ]
    winners = strs._pick_winners(rows, 1, 0.001)
    assert len(winners) == 1
    assert winners[0]["user_id"] == "alice"

    with tempfile.TemporaryDirectory() as tmp:
        grants_path = os.path.join(tmp, "staking_trophy_grants.jsonl")
        with open(grants_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"interval_id": "iv-1", "user_id": "alice"}) + "\n")

        with patch.object(strs, "_GRANTS_PATH", grants_path):
            result = strs.process_interval_winners(rows, interval_id="iv-1")
            assert result["skipped"] is True
            assert result["reason"] == "already_granted"


def test_process_interval_winners_grants_block_trophy():
    from backend.services import staking_trophy_reward_service as strs

    rows = [{"user_id": "staking_winner_user", "reward_mn2": 0.25}]
    grant_result = {
        "success": True,
        "edition_key": "TRO-block-1000-1",
        "license_number": "MN2-BLK-LIC-1000-ABC",
        "block_height": 1000,
    }

    with tempfile.TemporaryDirectory() as tmp:
        grants_path = os.path.join(tmp, "staking_trophy_grants.jsonl")
        with patch.object(strs, "_GRANTS_PATH", grants_path):
            with patch.object(strs, "_find_grant_height", return_value=1000):
                with patch.object(strs, "grant_staking_block_trophy", return_value=grant_result):
                    with patch.object(strs, "on_staking_trophy_grant", create=True):
                        result = strs.process_interval_winners(rows, interval_id="iv-new")
                        assert result["success"] is True
                        assert result["granted"] == 1
                        assert result["grants"][0]["block_height"] == 1000
                        assert result["grants"][0]["license_number"] == "MN2-BLK-LIC-1000-ABC"

                        user_grants = strs.user_staking_trophy_grants("staking_winner_user")
                        assert user_grants["count"] == 1
                        assert user_grants["grants"][0]["interval_id"] == "iv-new"


def test_claim_block_trophy_staking_reward_no_payment():
    from backend.services import block_mint_service as bms
    from backend.services import trophy_fulfillment_service as tfs

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
                            "license_number": "MN2-BLK-LIC-1000-TEST",
                        }
                    },
                    "last_height": 1000,
                },
                f,
            )
        counters = os.path.join(tmp, "trophy_edition_counters.json")
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            with patch.object(tfs, "_EDITION_COUNTERS_PATH", counters):
                with patch("backend.services.block_trophy_battle_service.generate_battle_stats") as mock_battle:
                    mock_battle.return_value = {"power": 10, "defense": 5}
                    with patch("backend.services.block_trophy_registry_service.build_trading_profile") as mock_trade:
                        mock_trade.return_value = {"peer_transfer": True, "auction_listable": True}
                        os.environ["MASTERNODER_LOG_DIR"] = tmp
                        try:
                            uid = "staking_reward_test_user"
                            result = bms.claim_block_trophy_staking_reward(
                                uid,
                                1000,
                                interval_id="iv-test",
                                reward_mn2=0.42,
                            )
                            assert result["success"] is True
                            assert result.get("edition_key")
                            editions = tfs.get_trophy_editions(uid, "block-1000")
                            assert len(editions) == 1
                            assert editions[0]["acquired_via"] == "staking_winner"
                        finally:
                            os.environ.pop("MASTERNODER_LOG_DIR", None)
