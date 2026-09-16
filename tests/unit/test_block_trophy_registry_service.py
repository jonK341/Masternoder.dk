"""Per-block trophy registry — license + trading metadata."""
from __future__ import annotations

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_license_number_deterministic():
    from backend.services.block_trophy_registry_service import license_number

    a = license_number(998208)
    b = license_number(998208)
    assert a == b
    assert a.startswith("MN2-BLK-LIC-")
    assert "998208" in a


def test_trading_profile_one_per_block():
    from backend.services.block_trophy_battle_service import generate_battle_stats
    from backend.services.block_trophy_registry_service import build_trading_profile

    stats = generate_battle_stats(1001, "TRO-block-1001-preview", edition_no=1)
    tp = build_trading_profile(1001, stats=stats, floor_price_usd=0.99)
    assert tp["uniqueness"] == "one_per_block"
    assert tp["supply"] == 1
    assert tp["auction_listable"] is True
    assert tp["peer_transfer"] is True
    assert tp["license_number"].startswith("MN2-BLK-LIC-")


def test_get_block_registry():
    from unittest.mock import patch
    import os
    import tempfile
    from backend.services import block_mint_service as bms

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "block_mint_manifest.json")
        with patch.object(bms, "_MANIFEST_PATH", manifest):
            with patch.object(bms, "_current_block_height", return_value=1010):
                reg = bms.get_block_registry(limit=5)
                assert reg["success"] is True
                assert reg["one_per_block"] is True
                assert len(reg["entries"]) >= 1
                entry = reg["entries"][0]
                assert entry.get("license_number")
                assert entry.get("trading_profile")
