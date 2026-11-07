"""Fleet inventory seed + bootstrap helpers."""
from __future__ import annotations


def test_seed_platform_inventory_dry_run(monkeypatch):
    import backend.services.mn2_fleet_inventory_ops as inv

    hosts: list = []

    def fake_load():
        return {"hosts": list(hosts)}

    def fake_register(payload):
        hosts.append(dict(payload))
        return {"success": True, "host": payload}

    import backend.services.mn2_masternode_service as mn

    monkeypatch.setattr(mn, "_load_hosts_doc", fake_load)
    monkeypatch.setattr(mn, "register_host", fake_register)
    monkeypatch.setattr(
        mn,
        "get_config",
        lambda: {"max_hosted_nodes": 500, "collateral_mn2": 5000},
    )
    monkeypatch.setattr(mn, "_count_slots_used", lambda h: len(h))

    dry = inv.seed_platform_inventory_hosts(3, dry_run=True)
    assert dry["would_create"] == 3

    live = inv.seed_platform_inventory_hosts(3, dry_run=False)
    assert live["created"] == 3
    assert hosts[0]["id"] == "platform-mn-1"
    assert hosts[0]["status"] == "queued"
