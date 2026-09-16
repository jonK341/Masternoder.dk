"""Plan 003 — trophy provenance chain."""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_provenance_append_and_chain():
    from backend.services import trophy_provenance_service as tps

    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "trophy_provenance.jsonl")
        with patch.object(tps, "_LOG_PATH", log_path):
            tps.append_event("TRO-block-1-1", "minted", user_id="alice")
            tps.append_event("TRO-block-1-1", "auction_sale", from_user_id="alice", to_user_id="bob")
            chain = tps.get_chain("TRO-block-1-1")
            assert chain["count"] == 2
            assert chain["events"][0]["event_type"] == "minted"
