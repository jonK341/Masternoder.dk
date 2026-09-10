"""Masternode hosting slot / waiting queue counters."""
from backend.services.mn2_masternode_service import _count_waiting_slots, _count_slots_used


def test_waiting_slots_counts_queued_and_provisioning():
    hosts = [
        {"id": "a", "status": "active"},
        {"id": "b", "status": "queued"},
        {"id": "c", "status": "provisioning", "collateral_txid": "tx1"},
        {"id": "d", "status": "provisioning"},
        {"id": "e", "status": "planned"},
    ]
    assert _count_waiting_slots(hosts) == 4
    assert _count_slots_used(hosts) == 4  # active + queued + planned + provisioning w/ txid
