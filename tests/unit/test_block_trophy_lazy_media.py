"""High-priority lazy media + genesis backfill progress metrics."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_count_block_media_stats():
    from backend.services.block_trophy_media_service import count_block_media_stats

    with tempfile.TemporaryDirectory() as tmp:
        img_dir = os.path.join(tmp, "static", "img", "trophies")
        os.makedirs(img_dir, exist_ok=True)
        with open(os.path.join(img_dir, "block-10.gif"), "wb") as f:
            f.write(b"gif")

        with patch("backend.services.block_trophy_media_service._BASE", tmp):
            stats = count_block_media_stats([10, 11, 12])

    assert stats["media_generated_count"] == 1
    assert stats["media_pending_count"] == 2
    assert stats["media_total_drops"] == 3
    assert stats["media_percent_complete"] == 33.33


def test_genesis_backfill_status_includes_media_progress():
    from backend.services import block_mint_service as bms

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "block_mint_manifest.json")
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "drops": {"1": {"height": 1}, "2": {"height": 2}},
                    "last_height": 100,
                    "genesis_backfill_started": True,
                    "genesis_backfill_cursor": 3,
                },
                f,
            )
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            with patch("backend.services.block_trophy_media_service.count_block_media_stats") as mock_count:
                mock_count.return_value = {
                    "media_generated_count": 1,
                    "media_pending_count": 1,
                    "media_total_drops": 2,
                    "media_percent_complete": 50.0,
                }
                status = bms.get_genesis_backfill_status()

    assert status["success"] is True
    assert status["media_percent_complete"] == 50.0
    assert status["genesis_index_percent"] == 2.0
    assert status["total_drops"] == 2


def test_priority_broadcast_skips_low_priority():
    from backend.services import trophy_anchor_service as tas

    cfg = {
        "broadcast_on_chain": True,
        "broadcast_priority_only": True,
        "broadcast_min_priority": 50,
    }
    low = {"source": "paypal", "priority": 25}
    high = {"source": "staking_winner", "priority": 100}

    assert tas._should_broadcast(low, cfg) is False
    assert tas._should_broadcast(high, cfg) is True


def test_ensure_lazy_edition_media_skips_when_file_exists():
    from backend.services.block_trophy_media_service import ensure_lazy_edition_media

    with tempfile.TemporaryDirectory() as tmp:
        editions = os.path.join(tmp, "static", "img", "trophies", "editions")
        os.makedirs(editions, exist_ok=True)
        gif_path = os.path.join(editions, "TRO-block-1-1.gif")
        with open(gif_path, "wb") as f:
            f.write(b"gif")

        edition = {
            "gif_url": "/static/img/trophies/editions/TRO-block-1-1.gif",
            "block_height": 1,
            "edition_no": 1,
            "item_id": "block-1",
        }
        with patch("backend.services.block_trophy_media_service._BASE", tmp):
            with patch("backend.services.block_mint_service.get_config", return_value={"lazy_media_generation": True}):
                out = ensure_lazy_edition_media(edition, "TRO-block-1-1")

    assert out["gif_url"] == edition["gif_url"]
