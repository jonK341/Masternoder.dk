"""Block 1,000,000 genesis trophy announcement + backfill config."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_build_announcement_payload():
    from backend.services.trophy_milestone_announcement_service import (
        GENESIS_BLOCK,
        MILESTONE_BLOCK,
        build_block_million_announcement_payload,
    )

    payload = build_block_million_announcement_payload()
    assert "1,000,000" in payload["content"]
    embed = payload["embeds"][0]
    assert str(GENESIS_BLOCK) in embed["description"]
    assert "1,000,000" in embed["fields"][0]["value"]


def test_post_announcement_publishes_news():
    from backend.services import trophy_milestone_announcement_service as tmas

    with patch("backend.services.discord_service.post_message", return_value={"success": True}) as post:
        with patch("backend.services.platform_news_publish.publish", return_value={"success": True}) as pub:
            result = tmas.post_block_million_announcement()
            assert result["success"] is True
            post.assert_called_once()
            pub.assert_called_once()


def test_genesis_backfill_starts_at_milestone():
    from backend.services import block_mint_service as bms

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "manifest.json")
        config = os.path.join(tmp, "config.json")
        with open(config, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "enabled": True,
                    "lookback_blocks": 5,
                    "milestone_block": 1000000,
                    "genesis_block": 1,
                    "backfill_from_genesis_at_milestone": True,
                    "backfill_batch_size": 10,
                    "milestone_discord_announced": True,
                },
                f,
            )
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            with patch.object(bms, "_CONFIG_PATH", config):
                with patch.object(bms, "_current_block_height", return_value=1_000_000):
                    with patch("backend.services.block_trophy_media_service.ensure_block_media"):
                        with patch("backend.services.trophy_milestone_announcement_service.post_block_million_announcement"):
                            sync = bms.sync_block_height()
                            assert sync["success"] is True
                            assert sync.get("genesis_backfill") is True
                            assert len(sync["added"]) == 50
                            doc = bms._read_json(manifest, {})
                            assert doc.get("genesis_backfill_cursor") == 51
