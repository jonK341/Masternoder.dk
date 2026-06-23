"""Tests for master-plan wave A infrastructure services."""
from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_conservation_gate_structure():
    from backend.services.mn2_conservation_gate import conservation_gate

    r = conservation_gate()
    assert r["success"] is True
    assert r["verdict"] in ("green", "amber", "red")
    assert isinstance(r["checks"], list)


def test_agent_kill_switch_global_halt(monkeypatch):
    from backend.services import agent_kill_switch as ks

    path = os.path.join(_ROOT, "data", "_test_agent_kill_switch.json")
    monkeypatch.setattr(ks, "_PATH", path)
    try:
        ks.set_switch(global_halt=False, reason="test")
        assert ks.check_action("stake")["allowed"] is True
        ks.set_switch(global_halt=True, reason="emergency")
        blocked = ks.check_action("stake")
        assert blocked["allowed"] is False
        assert blocked["code"] == "global_halt"
    finally:
        if os.path.isfile(path):
            os.remove(path)


def test_p2p_oracle_skips_when_no_price(monkeypatch):
    from backend.services import mn2_p2p_oracle as oracle

    monkeypatch.setattr(oracle, "_oracle_usd", lambda: None)
    v = oracle.validate_listing_price(0.01)
    assert v["allowed"] is True
    assert v.get("oracle_skipped") is True


def test_p2p_oracle_blocks_outside_corridor(monkeypatch):
    from backend.services import mn2_p2p_oracle as oracle

    monkeypatch.setattr(
        oracle,
        "get_corridor",
        lambda spread_percent=None: {
            "oracle_available": True,
            "oracle_usd_per_mn2": 0.10,
            "min_price_usd_per_mn2": 0.08,
            "max_price_usd_per_mn2": 0.12,
            "spread_percent": 20,
        },
    )
    bad = oracle.validate_listing_price(0.50)
    assert bad["allowed"] is False
    assert bad["code"] == "price_outside_corridor"
    ok = oracle.validate_listing_price(0.10)
    assert ok["allowed"] is True


def test_balance_commit_reserve_and_abort(monkeypatch):
    from backend.services import mn2_balance_commit as bc

    commits_path = os.path.join(_ROOT, "data", "_test_pending_commits.json")
    monkeypatch.setattr(bc, "_PATH", commits_path)

    class FakePoints:
        def __init__(self):
            self.bal = 10.0

        def add_points(self, user_id, pt, amount, source="", metadata=None):
            self.bal += float(amount)
            return {"success": True, "balance": self.bal}

    fake = FakePoints()
    import backend.services.unified_points_database as upd

    monkeypatch.setattr(upd, "unified_points_db", fake)

    try:
        r = bc.begin_withdrawal("user_a", 3.0)
        assert r["success"] is True
        assert fake.bal == pytest.approx(7.0)
        assert bc.pending_amount_for_user("user_a") == pytest.approx(3.0)
        bc.abort(r["commit_id"], reason="test")
        assert fake.bal == pytest.approx(10.0)
        assert bc.pending_amount_for_user("user_a") == 0.0
    finally:
        if os.path.isfile(commits_path):
            os.remove(commits_path)


def test_hold_registry_assert(monkeypatch):
    from backend.services import mn2_hold_registry as hr

    monkeypatch.setattr(
        hr,
        "get_holds",
        lambda user_id: {
            "liquid_mn2": 10.0,
            "held_mn2": 3.0,
            "withdrawable_mn2": 7.0,
            "holds": [],
        },
    )
    assert hr.assert_withdrawable("u1", 8.0)["allowed"] is False
    assert hr.assert_withdrawable("u1", 5.0)["allowed"] is True
