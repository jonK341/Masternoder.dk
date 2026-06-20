"""Masternode provisioning RPC wrappers (MasterNoder2 v1.2.3+)."""

from __future__ import annotations

from backend.services import mn2_masternode_service as mn
from backend.services import mn2_rpc_client as rpc


def test_start_masternode_alias_uses_startmasternode(monkeypatch):
    calls = []

    def fake_start(set_type, lock_wallet, alias=None):
        calls.append((set_type, lock_wallet, alias))
        if set_type == "alias":
            return {"result": "ok", "error": None}
        return {"error": "skip", "result": None}

    monkeypatch.setattr(rpc, "startmasternode", fake_start)
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)

    assert mn._start_masternode_alias("platformmn2") is None
    assert calls[0] == ("alias", False, "platformmn2")


def test_startmasternode_passes_string_lock(monkeypatch):
    seen = {}

    def fake_start(set_type, lock_wallet, alias=None):
        seen["lock"] = lock_wallet
        return {"result": "ok", "error": None}

    import backend.services.mn2_rpc_client as rpc
    monkeypatch.setattr(rpc, "startmasternode", fake_start)
    from backend.services import mn2_masternode_service as mn
    monkeypatch.setattr(mn, "_unlock_wallet", lambda: True)
    mn._start_masternode_alias("x")
    assert seen.get("lock") is False


def test_masternode_conf_line_field_order(tmp_path, monkeypatch):
    conf = tmp_path / "masternode.conf"
    monkeypatch.setattr(mn, "_masternode_conf_path", lambda: str(conf))
    mn._append_masternode_conf_line(
        "platformmn2", "140.82.39.124:17646", "abc123deadbeef", 0, "6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF",
    )
    assert conf.read_text().strip() == (
        "platformmn2 140.82.39.124:17646 6mD73mXp9wJQ8gftzD912WEQVkhtxPGamdUhkuazv2VVbKGLboF abc123deadbeef 0"
    )


def test_provision_uses_createmasternodekey(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "mn2_masternode_config.json").write_text(
        '{"max_hosted_nodes": 100, "auto_provision": true, "collateral_mn2": 10000, '
        '"ops": {"min_collateral_confirmations": 10}}',
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
    monkeypatch.setattr(mn, "_start_masternode_alias", lambda alias: None)
    monkeypatch.setattr(mn, "_broadcast_endpoint", lambda: "140.82.39.124:17646")

    seen = {}

    def fake_genkey():
        seen["genkey"] = True
        return {"result": "93HaYBVUCYjEMeeH1Y4sBGLALQZE1Yc1K64xiqgX37tGBDQL8Xg", "error": None}

    monkeypatch.setattr(rpc, "createmasternodekey", fake_genkey)
    monkeypatch.setattr(rpc, "masternode_command", lambda *a: {"error": "legacy"})

    out = mn.provision_host("platform-mn-9")
    assert seen.get("genkey") is True
    assert out.get("success") is True
