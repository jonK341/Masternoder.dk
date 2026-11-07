"""Camgirls payout audit, assignments, and chain reward helpers."""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from backend.services.camgirls_assignments_service import assign_performer, ensure_agent_model
from backend.services.camgirls_payout_service import audit_performer_wallets, payout_performer_reward_on_chain


@pytest.fixture()
def payout_file(tmp_path, monkeypatch):
    path = tmp_path / "camgirls_payout_addresses.json"
    monkeypatch.setattr(
        "backend.services.camgirls_payout_service._PAYOUT_FILE",
        str(path),
    )
    return path


def test_audit_flags_missing_address(payout_file, monkeypatch):
    payout_file.write_text(
        json.dumps({"performers": {"performer_nova": {"address": "mn2testaddr"}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "backend.services.camgirls_service.list_active_performer_ids",
        lambda: ["performer_nova", "performer_luna"],
    )
    monkeypatch.setattr(
        "backend.services.camgirls_service.get_performer_row",
        lambda pid: {"id": pid, "display_name": pid},
    )

    with patch("backend.services.camgirls_payout_service.validate_payout_address_on_chain") as v:
        v.return_value = {"checked": True, "isvalid": True, "address": "mn2testaddr"}
        out = audit_performer_wallets(check_rpc=True, sync_catalog=False)

    assert out["missing_address"] == 1
    assert out["with_address"] == 1


def test_payout_reward_dry_run(payout_file, monkeypatch):
    payout_file.write_text(
        json.dumps({"performers": {"performer_nova": {"address": "mn2addr1"}}}),
        encoding="utf-8",
    )
    out = payout_performer_reward_on_chain(
        "performer_nova",
        0.0002,
        source="test",
        reference="camgirl-assign:performer_nova",
        dry_run=True,
    )
    assert out["success"] is True
    assert out.get("dry_run") is True
    assert out["address"] == "mn2addr1"


def test_ensure_agent_model_creates_stub(tmp_path, monkeypatch):
    models = tmp_path / "camgirls_agent_models.json"
    models.write_text(json.dumps({"agents": []}), encoding="utf-8")
    assigns = tmp_path / "camgirls_assignments.json"
    assigns.write_text(json.dumps({"assignments": {}}), encoding="utf-8")
    monkeypatch.setattr("backend.services.camgirls_assignments_service._MODELS_FILE", str(models))
    monkeypatch.setattr("backend.services.camgirls_assignments_service._ASSIGNMENTS_FILE", str(assigns))
    monkeypatch.setattr(
        "backend.services.camgirls_service.get_performer_row",
        lambda pid: {"id": pid, "display_name": "Wave Host"},
    )

    created = ensure_agent_model("performer_wave9_demo_host")
    assert created["created"] is True
    assert created["agent"]["agent_id"].startswith("camgirl_agent_")


def test_assign_performer_records_assignment(tmp_path, monkeypatch, payout_file):
    payout_file.write_text(
        json.dumps({"performers": {"performer_nova": {"address": "mn2addr1"}}}),
        encoding="utf-8",
    )
    models = tmp_path / "models.json"
    models.write_text(
        json.dumps(
            {
                "agents": [
                    {
                        "agent_id": "camgirl_agent_nova",
                        "performer_id": "performer_nova",
                        "display_name": "Nova Agent",
                        "task_kind": "creative",
                        "casino_skill_set": ["studio_host"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assigns = tmp_path / "assignments.json"
    assigns.write_text(json.dumps({"assignments": {}}), encoding="utf-8")
    monkeypatch.setattr("backend.services.camgirls_assignments_service._MODELS_FILE", str(models))
    monkeypatch.setattr("backend.services.camgirls_assignments_service._ASSIGNMENTS_FILE", str(assigns))
    monkeypatch.setattr(
        "backend.services.camgirls_service.get_performer_row",
        lambda pid: {"id": pid, "display_name": "Nova"},
    )

    out = assign_performer("performer_nova", reward_on_chain=True, dry_run=True)
    assert out["success"] is True
    assert out["payout_address"] == "mn2addr1"
    assert out["chain_reward"].get("dry_run") is True
    data = json.loads(assigns.read_text(encoding="utf-8"))
    assert "performer_nova" in data["assignments"]
