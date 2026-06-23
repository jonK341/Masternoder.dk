"""
Unit tests for the explorer daemon-stats enrichment (V9.2 network monitor).

Covers mn2_chainz.daemon_extras() field mapping (RPC mocked) and that the
network-history snapshot captures the new connections/mempool_tx keys.
"""
import json
import os
import shutil
import tempfile

import pytest

from backend.services import mn2_chainz
from backend.services import mn2_rpc_client as rpc
from backend.services import mn2_network_stats as stats


@pytest.fixture(autouse=True)
def _clear_daemon_cache():
    mn2_chainz._DAEMON_CACHE.clear()
    yield
    mn2_chainz._DAEMON_CACHE.clear()


def test_daemon_extras_maps_rpc_fields(monkeypatch):
    monkeypatch.setattr(rpc, "getconnectioncount", lambda timeout_sec=None: {"result": 8, "error": None})
    monkeypatch.setattr(rpc, "getnetworkinfo", lambda: {"result": {
        "version": 190000, "subversion": "/MN2:1.9/", "protocolversion": 70015, "connections": 8}, "error": None})
    monkeypatch.setattr(rpc, "getmempoolinfo", lambda: {"result": {"size": 3, "bytes": 1200}, "error": None})
    monkeypatch.setattr(rpc, "getblockchaininfo", lambda: {"result": {
        "chain": "main", "verificationprogress": 0.9999, "mediantime": 111,
        "size_on_disk": 123456, "headers": 500}, "error": None})
    monkeypatch.setattr(rpc, "getinfo", lambda: {"result": {"moneysupply": 21000000}, "error": None})

    de = mn2_chainz.daemon_extras()
    assert de["reachable"] is True
    assert de["connections"] == 8
    assert de["mempool_tx"] == 3
    assert de["mempool_bytes"] == 1200
    assert de["version"] == 190000
    assert de["subversion"] == "/MN2:1.9/"
    assert de["chain"] == "main"
    assert de["size_on_disk"] == 123456
    assert de["money_supply"] == 21000000


def test_daemon_extras_unreachable_is_safe(monkeypatch):
    err = {"result": None, "error": "connection refused"}
    for name in ("getconnectioncount", "getnetworkinfo", "getmempoolinfo", "getblockchaininfo", "getinfo"):
        if name == "getconnectioncount":
            monkeypatch.setattr(rpc, name, lambda timeout_sec=None: dict(err))
        else:
            monkeypatch.setattr(rpc, name, lambda: dict(err))
    de = mn2_chainz.daemon_extras()
    assert de["reachable"] is False
    assert de["connections"] is None
    assert de["money_supply"] is None


def test_snapshot_captures_connections_and_mempool(monkeypatch):
    assert "connections" in stats._SNAPSHOT_KEYS
    assert "mempool_tx" in stats._SNAPSHOT_KEYS

    tmp_dir = tempfile.mkdtemp(prefix="mn2_hist_test_")
    hist_path = os.path.join(tmp_dir, "history.jsonl")
    monkeypatch.setattr(stats, "_history_path", lambda: hist_path)
    monkeypatch.setattr(stats, "_alerts_path", lambda: os.path.join(tmp_dir, "alerts.jsonl"))
    try:
        overview = {
            "block_height": 1000, "mn2_usd_price": 0.5, "difficulty": 12.3,
            "network_hashps": 999, "staking_weight": 999, "masternode_count": 4,
            "pool_total_staked": 100.0, "connections": 8, "mempool_tx": 3,
            "staking_health": {"staking_active": True},
        }
        res = stats.record_snapshot(overview, force=True)
        assert res["recorded"] is True
        rows = stats.get_history(hours=1, limit=10)
        assert rows and rows[-1]["connections"] == 8 and rows[-1]["mempool_tx"] == 3
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
