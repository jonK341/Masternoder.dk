"""Masternode hosting slot counting and stale host purge."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from backend.services import mn2_masternode_service as mn


def _iso_hours_ago(hours: float) -> str:
    ts = datetime.now(timezone.utc) - timedelta(hours=hours)
    return ts.isoformat().replace("+00:00", "Z")


@pytest.fixture
def hosts_file(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    hosts_path = data_dir / "mn2_masternode_hosts.json"
    cfg_path = data_dir / "mn2_masternode_config.json"
    cfg_path.write_text(json.dumps({"max_hosted_nodes": 50, "stale_provisioning_hours": 6}), encoding="utf-8")

    def _data_path(name: str) -> str:
        return str(data_dir / name)

    monkeypatch.setattr(mn, "_data_path", _data_path)
    monkeypatch.setattr(mn, "_CONFIG_FILE", "mn2_masternode_config.json")
    monkeypatch.setattr(mn, "_HOSTS_FILE", "mn2_masternode_hosts.json")
    return hosts_path


def _write_hosts(path, hosts):
    path.write_text(json.dumps({"hosts": hosts}), encoding="utf-8")


def test_count_slots_excludes_stuck_provisioning(hosts_file):
    _write_hosts(hosts_file, [
        {"id": "platform-mn-1", "label": "A", "status": "active"},
        {"id": "platform-mn-2", "label": "B", "status": "queued"},
        {"id": "ghost-1", "label": "G", "status": "provisioning"},
        {
            "id": "paid-1",
            "label": "P",
            "status": "provisioning",
            "collateral_txid": "abc",
            "collateral_vout": 0,
        },
    ])
    hosts = mn.list_hosts(include_internal=True)
    assert mn._count_slots_used(hosts) == 3


def test_purge_removes_old_provisioning_without_collateral(hosts_file):
    _write_hosts(hosts_file, [
        {"id": "keep-active", "label": "A", "status": "active"},
        {
            "id": "remove-me",
            "label": "G",
            "status": "provisioning",
            "created_at": _iso_hours_ago(24),
        },
        {
            "id": "keep-fresh",
            "label": "F",
            "status": "provisioning",
            "created_at": _iso_hours_ago(1),
        },
    ])
    result = mn.purge_stale_provisioning_hosts(max_age_hours=6, dry_run=False)
    assert "remove-me" in result["removed"]
    assert "keep-fresh" not in result["removed"]
    assert result["slots_used"] == 1


def test_purge_force_no_collateral(hosts_file):
    _write_hosts(hosts_file, [
        {"id": "ghost", "label": "G", "status": "provisioning", "created_at": _iso_hours_ago(0.1)},
    ])
    result = mn.purge_stale_provisioning_hosts(force_no_collateral=True, dry_run=False)
    assert result["removed"] == ["ghost"]
    assert result["slots_used"] == 0
