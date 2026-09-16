"""Plan 003 — trophy metadata and proof APIs."""
from __future__ import annotations

from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_build_metadata_from_edition():
    from backend.services.trophy_metadata_service import build_metadata

    edition = {
        "item_id": "block-1000",
        "item_name": "Block #1000",
        "edition_no": 1,
        "edition_key": "TRO-block-1000-1",
        "block_height": 1000,
        "license_number": "MN2-BLK-LIC-1000-X",
        "acquired_via": "block_mint",
        "gif_url": "/static/img/trophies/editions/TRO-block-1000-1.gif",
        "battle_stats": {"rarity": "rare", "mood": "fierce", "combat_rating": 88},
        "trading_profile": {"royalty_bps": 250},
    }
    with patch(
        "backend.services.trophy_metadata_service.find_edition_globally",
        return_value={"success": True, "user_id": "user_a", "edition": edition},
    ):
        with patch("backend.services.trophy_anchor_service.get_anchor_status", return_value={"success": True, "anchor_status": "committed"}):
            result = build_metadata("TRO-block-1000-1")
    assert result["success"] is True
    meta = result["metadata"]
    assert meta["name"] == "Block #1000"
    assert meta["royalty_bps"] == 250
    assert any(a["trait_type"] == "Block" for a in meta["attributes"])


def test_build_proof_page():
    from backend.services.trophy_proof_service import build_proof_page

    with patch(
        "backend.services.trophy_metadata_service.build_metadata",
        return_value={
            "success": True,
            "owner_id": "user_a",
            "metadata": {"name": "Test"},
            "edition": {"edition_key": "TRO-block-1-1", "gif_url": "/x.gif"},
        },
    ):
        with patch("backend.services.trophy_provenance_service.get_chain", return_value={"events": []}):
            proof = build_proof_page("TRO-block-1-1")
    assert proof["success"] is True
    assert proof["proof_url"].startswith("/trophy/proof")
