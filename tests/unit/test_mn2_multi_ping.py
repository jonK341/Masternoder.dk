"""Multi-ping fleet helpers (daemon v1.3+ site integration)."""

from __future__ import annotations

import json

import pytest

from backend.services import mn2_masternode_service as mn
from backend.services import mn2_rpc_client as rpc


@pytest.fixture
def hosts_file(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    hosts_path = data_dir / "mn2_masternode_hosts.json"
    cfg_path = data_dir / "mn2_masternode_config.json"
    cfg_path.write_text(
        json.dumps({"max_hosted_nodes": 50, "stale_provisioning_hours": 6, "enabled": True}),
        encoding="utf-8",
    )

    def _data_path(name: str) -> str:
        return str(data_dir / name)

    monkeypatch.setattr(mn, "_data_path", _data_path)
    return hosts_path


def _write_hosts(path, hosts):
    path.write_text(json.dumps({"hosts": hosts}), encoding="utf-8")


def test_parse_daemon_version_tuple():
    assert mn._parse_daemon_version_tuple("1.3.0.0-abc") == (1, 3, 0, 0)
    assert mn._parse_daemon_version_tuple("1.2.3.0") == (1, 2, 3, 0)
    assert mn._parse_daemon_version_tuple("bad") == (0, 0, 0, 0)
    # Bitcoin-style packed ints from getinfo (v1.2.3.0 / v1.3.0.0)
    assert mn._parse_daemon_version_tuple(1020300) == (1, 2, 3, 0)
    assert mn._parse_daemon_version_tuple("1020300") == (1, 2, 3, 0)
    assert mn._parse_daemon_version_tuple(1030000) == (1, 3, 0, 0)
    # Protocol ints on masternode rows are not product versions
    assert mn._parse_daemon_version_tuple(70916) == (0, 0, 0, 0)


def test_daemon_supports_multi_ping_true(monkeypatch):
    monkeypatch.setattr(rpc, "getinfo", lambda: {"result": {"version": "1.3.0.0-deadbeef"}, "error": None})
    assert mn.daemon_supports_multi_ping() is True


def test_daemon_supports_multi_ping_packed_int(monkeypatch):
    monkeypatch.setattr(rpc, "getinfo", lambda: {"result": {"version": 1030000}, "error": None})
    assert mn.daemon_supports_multi_ping() is True
    monkeypatch.setattr(rpc, "getinfo", lambda: {"result": {"version": 1020300}, "error": None})
    assert mn.daemon_supports_multi_ping() is False


def test_daemon_supports_multi_ping_false(monkeypatch):
    monkeypatch.setattr(rpc, "getinfo", lambda: {"result": {"version": "1.2.3.0-61caddb"}, "error": None})
    assert mn.daemon_supports_multi_ping() is False


def test_multi_ping_enabled_requires_daemon_support(monkeypatch):
    monkeypatch.setattr(mn, "_ops_cfg", lambda: {"multi_ping_enabled": True})
    monkeypatch.setattr(mn, "daemon_supports_multi_ping", lambda: False)
    assert mn.multi_ping_enabled() is False

    monkeypatch.setattr(mn, "daemon_supports_multi_ping", lambda: True)
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
    monkeypatch.setattr(mn, "_register_fleet_ping_targets", lambda: None)
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


def test_current_ping_metric_fleet_when_multi_ping(monkeypatch):
    monkeypatch.setattr(mn, "multi_ping_enabled", lambda: True)
    monkeypatch.setattr(
        mn,
        "network_masternodes",
        lambda limit=100: {
            "list": [
                {"status": "ENABLED", "activetime": 10},
                {"status": "ENABLED", "activetime": 20},
            ]
        },
    )
    assert mn._current_ping_metric() == 2


def test_maintain_ping_multi_ping_registers_fleet(monkeypatch):
    calls = {"all": 0, "start": 0}

    def fake_register():
        calls["all"] += 1
        return None

    def fake_start(alias, privkey=None, *, conf_changed=False, skip_privkey_sync=False):
        calls["start"] += 1
        return None

    monkeypatch.setattr(mn, "_ping_loop_healthy", lambda: False)
    monkeypatch.setattr(mn, "_primary_ping_alias", lambda: "platformmn2")
    monkeypatch.setattr(mn, "_primary_ping_privkey", lambda: "testpk")
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 0)
    monkeypatch.setattr(mn, "multi_ping_enabled", lambda: True)
    monkeypatch.setattr(mn, "_register_fleet_ping_targets", fake_register)
    monkeypatch.setattr(mn, "_start_masternode", fake_start)

    out = mn.maintain_ping_loop()
    assert out.get("success") is True
    assert calls["all"] == 1
    assert calls["start"] == 1


def test_match_on_chain_prefers_txid_not_payee_confusion():
    host = {
        "collateral_txid": "abc123",
        "collateral_vout": 1,
        "collateral_address": "JCollateralOwnerXXXX",
        "broadcast_address": "140.82.39.124:17646",
    }
    chain = [
        {
            "txhash": "abc123",
            "outidx": 1,
            "addr": "JPayeeAddressYYYY",
            "status": "ENABLED",
            "activetime": 100,
        },
        {
            "txhash": "other",
            "addr": "JCollateralOwnerXXXX",
            "status": "ENABLED",
        },
    ]
    matched = mn._match_on_chain(host, chain)
    assert matched is not None
    assert matched["addr"] == "JPayeeAddressYYYY"


def test_match_on_chain_does_not_match_collateral_to_payee_addr():
    host = {
        "collateral_address": "JPayeeAddressYYYY",
        "broadcast_address": "140.82.39.124:17646",
    }
    chain = [{"txhash": "x", "addr": "JPayeeAddressYYYY", "status": "ENABLED"}]
    assert mn._match_on_chain(host, chain) is None


def test_get_service_status_does_not_purge(hosts_file, monkeypatch):
    called = {"purge": 0}

    def boom(*args, **kwargs):
        called["purge"] += 1
        raise AssertionError("purge must not run on public status")

    monkeypatch.setattr(mn, "purge_stale_provisioning_hosts", boom)
    monkeypatch.setattr(
        mn,
        "network_masternodes",
        lambda limit=100, fresh=False: {"list": [], "total": 0, "enabled": 0},
    )
    monkeypatch.setattr(mn, "list_collateral_outputs", lambda: {"success": True, "count": 2, "outputs": []})
    monkeypatch.setattr(mn, "daemon_supports_multi_ping", lambda: False)
    monkeypatch.setattr(mn, "multi_ping_enabled", lambda: False)

    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.staking_health",
        lambda: {"staking_active": False, "mnsync": True, "status": "inactive"},
    )
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.getinfo",
        lambda: {"result": {"version": 1020300}, "error": None},
    )

    _write_hosts(
        hosts_file,
        [
            {
                "id": "h1",
                "label": "A",
                "status": "active",
                "collateral_txid": "tx1",
                "collateral_vout": 0,
                "broadcast_address": "140.82.39.124:17646",
            }
        ],
    )
    with mn._STATUS_CACHE_LOCK:
        mn._STATUS_CACHE["value"] = None
        mn._STATUS_CACHE["ts"] = 0.0

    out = mn.get_service_status(fresh=True)
    assert out["success"] is True
    assert called["purge"] == 0
    assert out["collateral_outputs_available"] == 2
    # min(capacity residual 49, collateral 2) → 2
    assert out["slots_available"] == 2
    assert out["daemon"]["multi_ping_capable"] is False
    assert out["daemon"]["version_tuple"] == [1, 2, 3, 0]
