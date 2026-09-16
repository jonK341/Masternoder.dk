"""Plan 003 A-U1/A-U5 — trophy chain anchor queue + OP_RETURN broadcast."""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_queue_and_process_anchor():
    from backend.services import trophy_anchor_service as tas

    with tempfile.TemporaryDirectory() as tmp:
        queue = os.path.join(tmp, "queue.json")
        registry = os.path.join(tmp, "registry.json")
        with patch.object(tas, "_QUEUE_PATH", queue):
            with patch.object(tas, "_REGISTRY_PATH", registry):
                with patch.object(tas, "_patch_edition_anchor"):
                    q = tas.queue_edition_anchor(
                        user_id="alice",
                        item_id="top25-01",
                        edition_no=1,
                        edition_key="TRO-top25-01-1",
                        proof_hash="abc123",
                        source="paypal",
                    )
                    assert q["success"] is True
                    assert q["anchor_commitment"]

                    dup = tas.queue_edition_anchor(
                        user_id="alice",
                        item_id="top25-01",
                        edition_no=1,
                        edition_key="TRO-top25-01-1",
                        proof_hash="abc123",
                    )
                    assert dup.get("duplicate") is True

                    status = tas.get_anchor_status("TRO-top25-01-1")
                    assert status["success"] is True
                    assert status["anchor_status"] == "committed"
                    assert status["on_chain_mint"] is False

                    proc = tas.process_anchor_queue(limit=5)
                    assert proc["success"] is True
                    assert proc["processed"] == 0


def test_anchor_status_none():
    from backend.services import trophy_anchor_service as tas

    with tempfile.TemporaryDirectory() as tmp:
        registry = os.path.join(tmp, "registry.json")
        with patch.object(tas, "_REGISTRY_PATH", registry):
            status = tas.get_anchor_status("TRO-missing-1")

    assert status["success"] is True
    assert status["anchor_status"] == "none"


def test_op_return_payload_hex():
    from backend.services import trophy_anchor_service as tas

    commitment = "a" * 64
    payload = tas.op_return_payload_hex(commitment)
    assert payload.startswith("54524f01")
    assert len(bytes.fromhex(payload)) == 36


def test_broadcast_anchor_queue_mock_rpc():
    from backend.services import trophy_anchor_service as tas

    commitment = tas.anchor_commitment("TRO-top25-01-2", "proof99")

    with tempfile.TemporaryDirectory() as tmp:
        queue = os.path.join(tmp, "queue.json")
        registry = os.path.join(tmp, "registry.json")
        with patch.object(tas, "_QUEUE_PATH", queue):
            with patch.object(tas, "_REGISTRY_PATH", registry):
                with patch.object(tas, "_patch_edition_anchor"):
                    with patch.object(
                        tas,
                        "broadcast_anchor_op_return",
                        return_value={
                            "success": True,
                            "anchor_txid": "deadbeef1234",
                            "anchor_explorer_url": "/explorer?tx=deadbeef1234",
                        },
                    ):
                        with patch.object(tas, "get_config", return_value={"enabled": True}):
                            _write_registry = {
                                "anchors": {
                                    "TRO-top25-01-2": {
                                        "edition_key": "TRO-top25-01-2",
                                        "user_id": "alice",
                                        "item_id": "top25-01",
                                        "edition_no": 2,
                                        "anchor_commitment": commitment,
                                        "anchor_status": "committed",
                                    }
                                }
                            }
                            with open(registry, "w", encoding="utf-8") as f:
                                import json

                                json.dump(_write_registry, f)

                            result = tas.broadcast_anchor_queue(limit=5)
                            assert result["success"] is True
                            assert result["broadcasted"] == 1
                            assert result["entries"][0]["anchor_txid"] == "deadbeef1234"

                            status = tas.get_anchor_status("TRO-top25-01-2")
                            assert status["anchor_status"] == "anchored"
                            assert status["anchor_txid"] == "deadbeef1234"
