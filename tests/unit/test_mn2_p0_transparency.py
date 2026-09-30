"""P0 transparency helpers: APR honesty + PoR stale cache."""

from __future__ import annotations

import backend.services.mn2_proof_of_reserves_service as por
import backend.services.mn2_staking_service as staking


def test_public_apr_null_when_daemon_inactive(monkeypatch):
    monkeypatch.setattr(staking, "dynamic_apr", lambda: 8.0)
    out = staking.public_apr_status({"staking_active": False, "status": "inactive", "mnsync": True})
    assert out["apr_percent"] is None
    assert out["estimated_apr_percent"] == 8.0
    assert out["apr_status"] == "inactive"
    assert out["staking_active"] is False


def test_public_apr_live_when_daemon_active(monkeypatch):
    monkeypatch.setattr(staking, "dynamic_apr", lambda: 5.5)
    out = staking.public_apr_status({"staking_active": True, "status": "active", "mnsync": True})
    assert out["apr_percent"] == 5.5
    assert out["apr_status"] == "live"


def test_proof_of_reserves_returns_stale_while_building(monkeypatch):
    sample = {"success": True, "coverage_ratio": 1.2, "stale": False}
    with por._CACHE_LOCK:
        por._CACHE["por"] = sample
        por._CACHE["por_ts"] = 0.0  # expired fresh TTL
        por._BUILDING_POR = True
    try:
        out = por.proof_of_reserves(force=False)
        assert out["success"] is True
        assert out.get("stale") is True
        assert out["coverage_ratio"] == 1.2
    finally:
        with por._CACHE_LOCK:
            por._BUILDING_POR = False
            por._CACHE["por"] = None
            por._CACHE["por_ts"] = 0.0
