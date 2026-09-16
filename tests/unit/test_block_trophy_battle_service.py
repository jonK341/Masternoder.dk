"""Plan 004 — block smiley trophy battle stats and arena."""
from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_generate_battle_stats_deterministic():
    from backend.services.block_trophy_battle_service import generate_battle_stats, serial_number

    a = generate_battle_stats(1005, "TRO-block-1005-1", edition_no=1)
    b = generate_battle_stats(1005, "TRO-block-1005-1", edition_no=1)
    assert a == b
    assert a["power"] >= 35
    assert a["serial_number"] == serial_number(1005, 1)
    assert a["trophy_kind"] == "block_smiley"


def test_simulate_battle_produces_result():
    from backend.services.block_trophy_battle_service import generate_battle_stats, simulate_battle

    atk = generate_battle_stats(100, "TRO-block-100-1", edition_no=1)
    def_ = generate_battle_stats(101, "TRO-block-101-shadow", edition_no=0)
    out = simulate_battle(atk, def_)
    assert out["result"] in ("win", "loss", "draw")
    assert out["attacker_score"] > 0


def test_battle_with_trophy_rewards():
    from backend.services import block_trophy_battle_service as bts

    edition = {
        "edition_key": "TRO-block-2000-1",
        "item_id": "block-2000",
        "edition_no": 1,
        "block_height": 2000,
        "battle_stats": bts.generate_battle_stats(2000, "TRO-block-2000-1", edition_no=1),
    }

    mock_points = MagicMock()
    mock_points.add_points.return_value = {"success": True}

    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(bts, "_HISTORY_PATH", os.path.join(tmp, "hist.json")):
            with patch.object(bts, "_COOLDOWN_PATH", os.path.join(tmp, "cd.json")):
                with patch.object(bts, "_find_owned_edition", return_value=edition):
                    with patch("backend.services.unified_points_database.unified_points_db", mock_points):
                        result = bts.battle_with_trophy("alice", "TRO-block-2000-1")

    assert result["success"] is True
    assert result["result"] in ("win", "loss", "draw")
    assert "rewards" in result
    assert mock_points.add_points.called
