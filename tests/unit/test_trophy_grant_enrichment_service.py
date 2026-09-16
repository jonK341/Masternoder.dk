"""Per-edition AI GIF + post-grant enrichment pipeline."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_ensure_edition_media_generates_unique_gif():
    from backend.services import block_trophy_media_service as btm

    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(btm, "_BASE", tmp):
            a = btm.ensure_edition_media(
                "TRO-block-1000-1",
                1000,
                battle_stats={"mood": "fierce", "rarity": "epic", "serial_number": "SN-1000-1"},
                license_number="MN2-BLK-LIC-1000-TEST",
            )
            b = btm.ensure_edition_media(
                "TRO-block-1000-2",
                1000,
                battle_stats={"mood": "calm", "rarity": "common", "serial_number": "SN-1000-2"},
            )
            assert a["success"] is True
            assert b["success"] is True
            assert a.get("per_edition") is True
            assert a["gif_url"] != b["gif_url"]
            assert os.path.isfile(os.path.join(tmp, a["gif_url"].lstrip("/")))


def test_enrich_block_trophy_grant_per_edition_gif():
    from backend.services import trophy_grant_enrichment_service as tges

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = os.path.join(tmp, "trophy_grant_enrichment_config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "enabled": True,
                    "per_edition_gif": True,
                    "auto_auction_staking_wins": False,
                    "discord_staking_wins": False,
                    "profile_badge_staking_champion": False,
                    "team_pool_notify": False,
                    "battle_ready_notification": False,
                },
                f,
            )
        with patch.object(tges, "_CONFIG_PATH", cfg_path):
            with patch.object(tges, "_boost_anchor_priority", return_value={"success": True}):
                with patch("backend.services.block_trophy_media_service.ensure_edition_media") as mock_media:
                    with patch("backend.services.trophy_fulfillment_service.patch_edition_fields") as mock_patch:
                        mock_media.return_value = {
                            "success": True,
                            "gif_url": "/static/img/trophies/editions/TRO-block-1000-1.gif",
                            "image_url": "/static/img/trophies/editions/TRO-block-1000-1.png",
                            "per_edition": True,
                        }
                        result = tges.enrich_block_trophy_grant(
                            "user_a",
                            "block-1000",
                            1,
                            "TRO-block-1000-1",
                            "proofhash",
                            1000,
                            acquired_via="staking_winner",
                            battle_stats={"combat_rating": 88, "mood": "fierce"},
                        )
                        assert result["success"] is True
                        assert result["gif_url"] == "/static/img/trophies/editions/TRO-block-1000-1.gif"
                        mock_patch.assert_called_once()


def test_anchor_priority_staking_first():
    from backend.services import trophy_anchor_service as tas

    with tempfile.TemporaryDirectory() as tmp:
        queue = os.path.join(tmp, "queue.json")
        with patch.object(tas, "_QUEUE_PATH", queue):
            with patch.object(tas, "_REGISTRY_PATH", os.path.join(tmp, "registry.json")):
                with patch.object(tas, "_patch_edition_anchor"):
                    with patch.object(tas, "process_anchor_queue", return_value={"success": True}):
                        tas.queue_edition_anchor(
                            user_id="u1",
                            item_id="block-1",
                            edition_no=1,
                            edition_key="TRO-block-1-1",
                            proof_hash="a" * 64,
                            source="default",
                        )
                        tas.queue_edition_anchor(
                            user_id="u2",
                            item_id="block-2",
                            edition_no=1,
                            edition_key="TRO-block-2-1",
                            proof_hash="b" * 64,
                            source="staking_winner",
                        )
                        doc = tas._read_json(queue, {"jobs": []})
                        jobs = doc.get("jobs") or []
                        assert int(jobs[1].get("priority") or 0) > int(jobs[0].get("priority") or 0)
