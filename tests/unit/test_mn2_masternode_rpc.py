"""Masternode provisioning RPC wrappers (MasterNoder2 v1.2.3+)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from backend.services import mn2_masternode_service as mn
from backend.services import mn2_rpc_client as rpc


@pytest.fixture(autouse=True)
def _rpc_ready(monkeypatch):
    monkeypatch.setattr(mn, "_wait_for_rpc_ready", lambda timeout_sec=None: None)
    monkeypatch.setattr(
        rpc,
        "getblockcount",
        lambda timeout_sec=None: {"result": 1, "error": None},
    )


def test_start_masternode_uses_alias_then_local(monkeypatch):
    calls = []

    def fake_start(set_type, lock_wallet, alias=None):
        calls.append((set_type, lock_wallet, alias))
        if set_type == "alias":
            return {"result": "ok", "error": None}
        return {"error": "skip", "result": None}

    monkeypatch.setattr(rpc, "startmasternode", fake_start)
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 0)
    monkeypatch.setattr(mn, "_sync_masternode_daemon_privkey", lambda: (False, None))

    assert mn._start_masternode("platformmn2", "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF") is None
    assert calls[0] == ("alias", False, "platformmn2")


def test_start_masternode_falls_back_to_local(monkeypatch):
    calls = []

    def fake_start(set_type, lock_wallet, alias=None):
        calls.append((set_type, lock_wallet, alias))
        if set_type == "local":
            return {"result": "ok", "error": None}
        return {"error": "alias failed", "result": None}

    monkeypatch.setattr(rpc, "startmasternode", fake_start)
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 0)
    monkeypatch.setattr(mn, "_sync_masternode_daemon_privkey", lambda: (False, None))
    monkeypatch.setattr(mn, "_privkey_for_alias", lambda a: "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF")

    assert mn._start_masternode("platformmn2") is None
    assert calls[0] == ("alias", False, "platformmn2")
    assert calls[1][0] == "local"


def test_start_masternode_syncs_primary_privkey_not_alias(monkeypatch):
    """Provisioning platformmn5 must not write platformmn5 key into masternoder2.conf."""
    synced = {"pk": None}

    def fake_sync():
        synced["called"] = True
        return False, None

    monkeypatch.setattr(mn, "_sync_masternode_daemon_privkey", fake_sync)
    monkeypatch.setattr(mn, "_primary_ping_privkey", lambda: "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF")
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 0)
    monkeypatch.setattr(rpc, "startmasternode", lambda *a, **k: {"result": "ok", "error": None})

    mn5_key = "6kAVPkUosHavdYirMtUrmEnNcarvZ3qF4JT2kdmzUWiDAeLHyzC"
    assert mn._start_masternode("platformmn5", mn5_key) is None
    assert synced.get("called") is True


def test_start_masternode_syncs_privkey_and_restarts(monkeypatch):
    synced = {"called": False, "restarted": False}

    def fake_sync():
        synced["called"] = True
        return True, None

    def fake_restart():
        synced["restarted"] = True
        return None

    monkeypatch.setattr(mn, "_sync_masternode_daemon_privkey", fake_sync)
    monkeypatch.setattr(mn, "_restart_masternode_daemon", fake_restart)
    monkeypatch.setattr(mn, "_ops_cfg", lambda: {"restart_daemon_on_conf_change": True})
    monkeypatch.setattr(mn, "_wait_for_rpc_ready", lambda timeout_sec=120: None)
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 0)
    monkeypatch.setattr(rpc, "startmasternode", lambda *a, **k: {"result": "ok", "error": None})

    assert mn._start_masternode("platformmn2", "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF") is None
    assert synced["called"] and synced["restarted"]


def test_startmasternode_passes_string_lock(monkeypatch):
    seen = {}

    def fake_start(set_type, lock_wallet, alias=None):
        seen["lock"] = lock_wallet
        return {"result": "ok", "error": None}

    monkeypatch.setattr(rpc, "startmasternode", fake_start)
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_sync_masternode_daemon_privkey", lambda: (False, None))
    monkeypatch.setattr(mn, "_privkey_for_alias", lambda a: "testpk")
    mn._start_masternode("x")
    assert seen.get("lock") is False


def test_start_masternode_restarts_on_masternoder2_conf_sync_only(monkeypatch):
    restarted = {"n": 0}

    def fake_restart():
        restarted["n"] += 1
        return None

    monkeypatch.setattr(mn, "_sync_masternode_daemon_privkey", lambda: (False, None))
    monkeypatch.setattr(mn, "_restart_masternode_daemon", fake_restart)
    monkeypatch.setattr(mn, "_ops_cfg", lambda: {"restart_daemon_on_conf_change": True})
    monkeypatch.setattr(mn, "_wait_for_rpc_ready", lambda timeout_sec=120: None)
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 0)
    monkeypatch.setattr(rpc, "startmasternode", lambda *a, **k: {"result": "ok", "error": None})

    mn._start_masternode("platformmn2", "pk", conf_changed=False)
    assert restarted["n"] == 0

    # New masternode.conf line — alias RPC only, no daemon restart.
    mn._start_masternode("platformmn5", "pk", conf_changed=True)
    assert restarted["n"] == 0

    monkeypatch.setattr(mn, "_sync_masternode_daemon_privkey", lambda: (True, None))
    mn._start_masternode("platformmn2", "pk", conf_changed=False)
    assert restarted["n"] == 1


def test_sync_skips_write_when_already_correct(monkeypatch):
    conf_dir = Path(tempfile.mkdtemp(prefix="mn2sync_ok_"))
    mn_conf = conf_dir / "masternode.conf"
    dconf = conf_dir / "masternoder2.conf"
    pk = "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF"
    mn_conf.write_text(
        f"platformmn2 140.82.39.124:17646 {pk} abc123 0\n",
        encoding="utf-8",
    )
    dconf.write_text(
        "\n".join([
            "rpcuser=x",
            "listen=1",
            "port=17646",
            "externalip=140.82.39.124",
            "masternode=1",
            f"masternodeprivkey={pk}",
            "masternodeaddr=127.0.0.1:17646",
        ]) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mn, "_masternode_conf_path", lambda: str(mn_conf))
    monkeypatch.setattr(mn, "_masternoder2_conf_path", lambda: str(dconf))
    monkeypatch.setattr(mn, "_ops_cfg", lambda: {
        "primary_ping_alias": "platformmn2",
        "external_ip": "140.82.39.124",
        "masternode_port": 17646,
        "masternode_ping_addr": "127.0.0.1:17646",
    })

    changed, err = mn._sync_masternode_daemon_privkey()
    assert changed is False
    assert err is None
    assert pk in dconf.read_text(encoding="utf-8")


def test_sync_permission_denied_when_mismatch(monkeypatch):
    conf_dir = Path(tempfile.mkdtemp(prefix="mn2sync_ro_"))
    mn_conf = conf_dir / "masternode.conf"
    dconf = conf_dir / "masternoder2.conf"
    want = "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF"
    have = "6kAVPkUosHavdYirMtUrmEnNcarvZ3qF4JT2kdmzUWiDAeLHyzC"
    mn_conf.write_text(f"platformmn2 140.82.39.124:17646 {want} abc123 0\n", encoding="utf-8")
    dconf.write_text(f"masternodeprivkey={have}\n", encoding="utf-8")
    dconf.chmod(0o444)

    monkeypatch.setattr(mn, "_masternode_conf_path", lambda: str(mn_conf))
    monkeypatch.setattr(mn, "_masternoder2_conf_path", lambda: str(dconf))
    monkeypatch.setattr(mn, "_ops_cfg", lambda: {"primary_ping_alias": "platformmn2"})

    changed, err = mn._sync_masternode_daemon_privkey()
    assert changed is False
    assert err is not None
    assert "cannot write" in err


def test_maintain_ping_skips_when_healthy(monkeypatch):
    monkeypatch.setattr(mn, "_ping_loop_healthy", lambda: True)
    monkeypatch.setattr(mn, "_primary_ping_alias", lambda: "platformmn2")
    out = mn.maintain_ping_loop()
    assert out.get("skipped") is True


def test_maintain_ping_starts_local_when_unhealthy(monkeypatch):
    calls = []

    def fake_start(alias, privkey=None, *, conf_changed=False, skip_privkey_sync=False):
        calls.append((alias, conf_changed, skip_privkey_sync))
        return None

    monkeypatch.setattr(mn, "_ping_loop_healthy", lambda: False)
    monkeypatch.setattr(mn, "_primary_ping_alias", lambda: "platformmn2")
    monkeypatch.setattr(mn, "_primary_ping_privkey", lambda: "testpk")
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_unlock_collateral_utxos", lambda: 2)
    monkeypatch.setattr(mn, "_start_masternode", fake_start)

    out = mn.maintain_ping_loop()
    assert out.get("success") is True
    assert calls == [("platformmn2", False, True)]


def test_ping_loop_unhealthy_when_frozen_without_timestamp(monkeypatch):
    monkeypatch.setattr(
        mn,
        "_read_ping_watch",
        lambda: {"activetime": 156002},
    )
    monkeypatch.setattr(mn, "_write_ping_watch", lambda act: None)
    monkeypatch.setattr(mn, "_primary_ping_activetime", lambda: 156002)
    monkeypatch.setattr(mn, "_ops_cfg", lambda: {"ping_stall_minutes": 8})
    assert mn._ping_loop_healthy() is False


def test_ping_loop_unhealthy_after_stall_window(monkeypatch):
    from datetime import datetime, timedelta, timezone

    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    monkeypatch.setattr(
        mn,
        "_read_ping_watch",
        lambda: {"activetime": 156002, "ts": old_ts},
    )
    monkeypatch.setattr(mn, "_write_ping_watch", lambda act: None)
    monkeypatch.setattr(mn, "_primary_ping_activetime", lambda: 156002)
    monkeypatch.setattr(mn, "_ops_cfg", lambda: {"ping_stall_minutes": 8})
    assert mn._ping_loop_healthy() is False


def test_ping_loop_ignores_wrong_enabled_collateral(monkeypatch):
    """Watchdog must not treat other ENABLED rows as healthy when platformmn2 is ACTIVE @ 0."""
    txid = "4b41ef0ca3b797a766b3ce84453a2b29c5c1ee5c98b813a890b0eaf97d37ad48"

    monkeypatch.setattr(mn, "_primary_ping_alias", lambda: "platformmn2")
    monkeypatch.setattr(mn, "_collateral_for_alias", lambda a: (txid, 1))
    monkeypatch.setattr(
        mn,
        "network_masternodes",
        lambda limit=100: {
            "list": [
                {"txhash": "394d557b79042caf139f20b1e10423b85982b2c00cdc0dde6a2fd2bfbf4b5f78", "status": "ENABLED", "activetime": 687602},
                {"txhash": txid, "status": "ACTIVE", "activetime": 0},
            ]
        },
    )
    assert mn._primary_ping_activetime() == 0
    assert mn._ping_loop_healthy() is False


def test_masternode_conf_line_field_order(tmp_path, monkeypatch):
    conf = tmp_path / "masternode.conf"
    monkeypatch.setattr(mn, "_masternode_conf_path", lambda: str(conf))
    mn._append_masternode_conf_line(
        "platformmn2", "140.82.39.124:17646", "abc123deadbeef", 0, "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF",
    )
    assert conf.read_text().strip() == (
        "platformmn2 140.82.39.124:17646 6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF abc123deadbeef 0"
    )


def test_masternode_conf_rejects_malformed_append(monkeypatch):
    conf = Path(tempfile.mkdtemp(prefix="mn2conf_reject_")) / "masternode.conf"
    monkeypatch.setattr(mn, "_masternode_conf_path", lambda: str(conf))
    with pytest.raises(ValueError, match="invalid masternode.conf fields"):
        mn._append_masternode_conf_line(
            "platformmn2", "not-an-ip-port", "abc123deadbeef", 0, "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF",
        )


def test_masternode_conf_repair_dedupes_bad_duplicate(monkeypatch):
    conf = Path(tempfile.mkdtemp(prefix="mn2conf_repair_")) / "masternode.conf"
    monkeypatch.setattr(mn, "_masternode_conf_path", lambda: str(conf))
    pk = "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF"
    txid = "4b41ef0ca3b797a766b3ce84453a2b29c5c1ee5c98b813a890b0eaf97d37ad48"
    conf.write_text(
        f"platformmn2 140.82.39.124:17646 {pk} {txid} 1\n"
        f"platformmn2 {pk} {txid}\n",
        encoding="utf-8",
    )
    out = mn.repair_masternode_conf()
    assert out["changed"] is True
    assert conf.read_text().strip() == f"platformmn2 140.82.39.124:17646 {pk} {txid} 1"
    assert mn._collateral_for_alias("platformmn2") == (txid, 1)
    assert mn._privkey_for_alias("platformmn2") == pk


def test_masternode_conf_append_replaces_malformed_alias(monkeypatch):
    conf = Path(tempfile.mkdtemp(prefix="mn2conf_append_")) / "masternode.conf"
    monkeypatch.setattr(mn, "_masternode_conf_path", lambda: str(conf))
    pk = "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF"
    txid = "4b41ef0ca3b797a766b3ce84453a2b29c5c1ee5c98b813a890b0eaf97d37ad48"
    conf.write_text(f"platformmn2 {pk} {txid}\n", encoding="utf-8")
    assert mn._append_masternode_conf_line("platformmn2", "140.82.39.124:17646", txid, 1, pk) is True
    assert conf.read_text().count("platformmn2") == 1
    assert mn._privkey_for_alias("platformmn2") == pk


def test_alias_from_host_id_strips_spaces():
    assert mn._alias_from_host_id("platform-mn-9") == "platformmn9"
    assert mn._alias_from_host_id("user-Sander S-597747") == "userSanderS59774"
    assert " " not in mn._alias_from_host_id("user-Sander S-fb801e")


def test_provision_uses_createmasternodekey(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "mn2_masternode_config.json").write_text(
        '{"max_hosted_nodes": 100, "auto_provision": true, "collateral_mn2": 5000, '
        '"ops": {"min_collateral_confirmations": 10, "restart_daemon_on_provision": false}}',
        encoding="utf-8",
    )
    (data_dir / "mn2_masternode_hosts.json").write_text(
        '{"hosts": [{"id": "platform-mn-9", "label": "T", "status": "queued"}]}',
        encoding="utf-8",
    )

    def _data_path(name: str) -> str:
        return str(data_dir / name)

    monkeypatch.setattr(mn, "_data_path", _data_path)
    monkeypatch.setattr(mn, "_CONFIG_FILE", "mn2_masternode_config.json")
    monkeypatch.setattr(mn, "_HOSTS_FILE", "mn2_masternode_hosts.json")
    monkeypatch.setattr(mn, "network_masternodes", lambda **kw: {"list": []})
    monkeypatch.setattr(mn, "_pick_collateral_utxo", lambda exclude, min_conf=10: {
        "txid": "abc123",
        "vout": 1,
        "address": "MxAddr",
        "confirmations": 20,
    })
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    monkeypatch.setattr(mn, "_append_masternode_conf_line", lambda *a, **k: None)
    monkeypatch.setattr(mn, "_broadcast_endpoint", lambda: "140.82.39.124:17646")

    start_calls = []

    def fake_start(alias, privkey=None, *, conf_changed=False):
        start_calls.append((alias, privkey))
        return None

    monkeypatch.setattr(mn, "_start_masternode", fake_start)

    seen = {}

    def fake_genkey():
        seen["genkey"] = True
        return {"result": "93HaYBVUCYjEMeeH1Y4sBGLALQZE1Yc1K64xiqgX37tGBDQL8Xg", "error": None}

    monkeypatch.setattr(rpc, "createmasternodekey", fake_genkey)

    out = mn.provision_host("platform-mn-9")
    assert seen.get("genkey") is True
    assert out.get("success") is True
    assert start_calls and start_calls[0][0] == "platformmn9"
    assert start_calls[0][1] == "93HaYBVUCYjEMeeH1Y4sBGLALQZE1Yc1K64xiqgX37tGBDQL8Xg"
