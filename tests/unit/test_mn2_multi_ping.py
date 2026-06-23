"""Multi-ping fleet helpers (daemon v1.3+ site integration)."""

from __future__ import annotations

import pytest

from backend.services import mn2_masternode_service as mn
from backend.services import mn2_rpc_client as rpc


def test_parse_daemon_version_tuple():
    assert mn._parse_daemon_version_tuple("1.3.0.0-abc") == (1, 3, 0, 0)
    assert mn._parse_daemon_version_tuple("1.2.3.0") == (1, 2, 3, 0)
    assert mn._parse_daemon_version_tuple("bad") == (0, 0, 0, 0)


def test_daemon_supports_multi_ping_true(monkeypatch):
    monkeypatch.setattr(rpc, "getinfo", lambda: {"result": {"version": "1.3.0.0-deadbeef"}, "error": None})
    assert mn.daemon_supports_multi_ping() is True


def test_daemon_supports_multi_ping_false(monkeypatch):
    monkeypatch.setattr(rpc, "getinfo", lambda: {"result": {"version": "1.2.3.0-61caddb"}, "error": None})
    assert mn.daemon_supports_multi_ping() is False


def test_multi_ping_enabled_respects_ops_flag(monkeypatch):
    monkeypatch.setattr(mn, "_ops_cfg", lambda: {"multi_ping_enabled": True})
    monkeypatch.setattr(mn, "daemon_supports_multi_ping", lambda: False)
    assert mn.multi_ping_enabled() is True

    monkeypatch.setattr(mn, "_ops_cfg", lambda: {"multi_ping_enabled": False})
    monkeypatch.setattr(mn, "daemon_supports_multi_ping", lambda: True)
    assert mn.multi_ping_enabled() is False


def test_start_masternode_multi_ping_skips_missing(monkeypatch):
    calls = []

    def fake_start(set_type, lock_wallet, alias=None):
        calls.append((set_type, lock_wallet, alias))
        return {"result": "ok", "error": None}

    monkeypatch.setattr(mn, "multi_ping_enabled", lambda: True)
    monkeypatch.setattr(rpc, "startmasternode", fake_start)
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 0)
    monkeypatch.setattr(mn, "_sync_masternode_daemon_privkey", lambda: (False, None))
    monkeypatch.setattr(mn, "_privkey_for_alias", lambda a: "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF")
    monkeypatch.setattr(rpc, "getblockcount", lambda timeout_sec=None: {"result": 1, "error": None})

    assert mn._start_masternode("customermn1") is None
    assert calls == [("alias", False, "customermn1")]


def test_register_fleet_ping_targets_calls_all(monkeypatch):
    seen = {}

    def fake_all(set_type, lock):
        seen["call"] = (set_type, lock)
        return {"result": {}, "error": None}

    monkeypatch.setattr(mn, "multi_ping_enabled", lambda: True)
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 0)
    monkeypatch.setattr(rpc, "startmasternode", fake_all)

    assert mn._register_fleet_ping_targets() is None
    assert seen["call"] == ("all", False)


def test_count_enabled_with_activetime():
    rows = [
        {"status": "ENABLED", "activetime": 100},
        {"status": "ENABLED", "activetime": 0},
        {"status": "ACTIVE", "activetime": 0},
    ]
    assert mn._count_enabled_with_activetime(rows) == 1
