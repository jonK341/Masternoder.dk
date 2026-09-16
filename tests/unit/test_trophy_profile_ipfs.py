"""Profile equip + IPFS permanent metadata pinning."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_equip_trophy_on_profile():
    from backend.services import trophy_profile_service as tps

    edition = {
        "item_id": "block-42",
        "item_name": "Block Smiley Trophy #42",
        "edition_no": 1,
        "gif_url": "/static/img/trophies/block-42.gif",
    }
    mock_onboarding = MagicMock()
    mock_onboarding.get_user_profile.return_value = {"preferences": {}}
    mock_onboarding.update_user_profile.return_value = {"success": True}

    with patch("backend.services.trophy_metadata_service.find_edition_globally") as mock_find:
        mock_find.return_value = {"success": True, "user_id": "alice", "edition": edition}
        with patch("backend.services.user_onboarding.user_onboarding", mock_onboarding):
            result = tps.equip_trophy_on_profile("alice", "TRO-block-42-1")

    assert result["success"] is True
    assert result["edition_key"] == "TRO-block-42-1"
    prefs = mock_onboarding.update_user_profile.call_args[0][1]["preferences"]
    assert prefs["trophy_badges"]["equipped_trophy_key"] == "TRO-block-42-1"


def test_equip_rejects_non_owner():
    from backend.services import trophy_profile_service as tps

    with patch("backend.services.trophy_metadata_service.find_edition_globally") as mock_find:
        mock_find.return_value = {"success": True, "user_id": "bob", "edition": {}}
        result = tps.equip_trophy_on_profile("alice", "TRO-block-42-1")

    assert result["success"] is False
    assert result["error"] == "not_owner"


def test_pin_edition_metadata_content_addressed():
    from backend.services import trophy_ipfs_service as tipfs

    meta_payload = {
        "success": True,
        "metadata": {"name": "Test Trophy", "edition_key": "TRO-test-1", "attributes": []},
        "edition": {"item_id": "block-1", "edition_no": 1},
        "owner_id": "alice",
    }

    with tempfile.TemporaryDirectory() as tmp:
        manifest = os.path.join(tmp, "data", "trophy_ipfs_manifest.json")
        with patch.object(tipfs, "_BASE", tmp):
            with patch.object(tipfs, "_MANIFEST_PATH", manifest):
                with patch("backend.services.trophy_metadata_service.build_metadata", return_value=meta_payload):
                    with patch("backend.services.trophy_fulfillment_service.patch_edition_fields"):
                        first = tipfs.pin_edition_metadata("TRO-test-1")
                        second = tipfs.pin_edition_metadata("TRO-test-1")
                        storage = tipfs._storage_dir()
                        assert first["success"] is True
                        assert first["ipfs_uri"].startswith("ipfs://")
                        assert os.path.isfile(os.path.join(storage, f"{first['digest']}.json"))
                        assert second.get("skipped") is True


def test_content_digest_stable():
    from backend.services.trophy_ipfs_service import content_digest

    a = content_digest({"b": 2, "a": 1})
    b = content_digest({"a": 1, "b": 2})
    assert a == b
    assert len(a) == 64
