"""Plan 003 A-U3 — transfer hooks re-anchor + provenance."""
from __future__ import annotations

from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_on_edition_transferred_peer():
    from backend.services.trophy_transfer_hooks import on_edition_transferred

    edition = {
        "edition_key": "TRO-block-5-1",
        "item_id": "block-5",
        "edition_no": 1,
        "proof_hash": "a" * 64,
    }
    with patch("backend.services.trophy_provenance_service.append_event", return_value={"success": True}) as prov:
        with patch("backend.services.trophy_anchor_service.queue_transfer_reanchor", return_value={"success": True}) as anchor:
            result = on_edition_transferred(
                edition,
                from_user_id="alice",
                to_user_id="bob",
                transfer_type="peer_transfer",
            )
            assert result["success"] is True
            prov.assert_called_once()
            anchor.assert_called_once()
