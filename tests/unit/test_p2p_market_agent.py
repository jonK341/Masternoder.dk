#!/usr/bin/env python3
"""Unit tests for P2P market agent cron service."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import backend.services.mn2_p2p_service as p2p
from backend.services.p2p_market_agent_service import (
    AGENT_PREFIX,
    _agent_ids,
    ensure_agents,
    run_p2p_market_agent_job,
    simulate_trades,
)


class FakePoints:
    def __init__(self):
        self.store = {}

    def add_points(self, uid, pt, amt, source=None, metadata=None):
        self.store.setdefault(uid, {}).setdefault(pt, 0.0)
        self.store[uid][pt] += float(amt)
        return {"success": True}

    def get_all_points(self, uid):
        s = self.store.get(uid, {})
        return {"success": True, "points": {"mn2_balance": float(s.get("mn2_balance", 0.0))}}


class P2PAgentBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_dir = p2p._data_dir
        p2p._data_dir = lambda: self.tmp
        self.fake = FakePoints()
        self._orig_points = p2p._points
        p2p._points = lambda: self.fake
        self._orig_ledger = p2p._ledger
        p2p._ledger = lambda *a, **k: None
        self._verified = patch.object(p2p, "_is_verified", return_value=True)
        self._verified.start()
        self._held = patch.object(p2p, "_onramp_held", return_value=0.0)
        self._held.start()
        self._cfg = patch.object(p2p, "get_config", return_value={
            "enabled": True, "model": "B", "platform_fee_percent": 2.5, "buyer_spread_percent": 1.0,
            "min_listing_mn2": 1.0, "max_listing_mn2": 5000.0, "max_open_listings_per_seller": 5,
            "requires_seller_verification": True, "seller_must_sell_cleared_only": True,
            "hold_hours": 72, "order_ttl_seconds": 900,
            "daily_usd_cap": 10000.0, "daily_usd_cap_verified": 100000.0,
            "lifetime_usd_cap_unverified": 500.0,
        })
        self._cfg.start()
        self._oracle = patch(
            "backend.services.mn2_p2p_oracle.validate_listing_price",
            return_value={"allowed": True},
        )
        self._oracle.start()
        self._add_verified = patch(
            "backend.services.mn2_verification.add_verified",
            return_value=True,
        )
        self._add_verified.start()
        self._is_verified = patch(
            "backend.services.mn2_verification.is_verified",
            return_value=True,
        )
        self._is_verified.start()

    def tearDown(self):
        p2p._data_dir = self._orig_dir
        p2p._points = self._orig_points
        p2p._ledger = self._orig_ledger
        self._verified.stop()
        self._held.stop()
        self._cfg.stop()
        self._oracle.stop()
        self._add_verified.stop()
        self._is_verified.stop()


class TestP2PAgentUsers(P2PAgentBase):
    def test_agent_ids_count(self):
        ids = _agent_ids()
        self.assertEqual(len(ids), 10)
        self.assertTrue(ids[0].startswith(AGENT_PREFIX))

    def test_is_agent_user(self):
        self.assertTrue(p2p.is_agent_user("p2p_agent_01"))
        self.assertFalse(p2p.is_agent_user("default_user"))


def _bankroll_agents(fake: FakePoints, mn2: float = 300.0) -> None:
    for uid in _agent_ids():
        fake.add_points(uid, "mn2_balance", mn2)


class TestP2PAgentSeed(P2PAgentBase):
    def test_ensure_agents_creates_listings(self):
        _bankroll_agents(self.fake)
        with patch(
            "backend.services.p2p_market_agent_service._ensure_balance",
            return_value=0.0,
        ):
            res = ensure_agents(target_listings=5)
        self.assertTrue(res.get("success"))
        self.assertGreaterEqual(res.get("listings_created", 0), 1)
        listings = p2p.list_listings()
        self.assertGreaterEqual(len(listings.get("listings") or []), 1)


class TestP2PAgentTrade(P2PAgentBase):
    def test_simulate_trade_between_agents(self):
        _bankroll_agents(self.fake)
        with patch(
            "backend.services.p2p_market_agent_service._ensure_balance",
            return_value=0.0,
        ):
            ensure_agents(target_listings=3)
            out = simulate_trades(max_trades=1)
        self.assertTrue(out.get("success"))
        self.assertGreaterEqual(out.get("trades", 0), 1)

    def test_agent_simulate_rejects_non_agent(self):
        self.fake.add_points("p2p_agent_01", "mn2_balance", 100)
        listing = p2p.create_listing("p2p_agent_01", 50, 0.25)
        self.assertTrue(listing.get("success"), listing)
        res = p2p.agent_simulate_purchase("default_user", listing["listing_id"], 10)
        self.assertFalse(res.get("success"))

    def test_run_job_end_to_end(self):
        _bankroll_agents(self.fake)
        with patch(
            "backend.services.p2p_market_agent_service._ensure_balance",
            return_value=0.0,
        ):
            out = run_p2p_market_agent_job(target_listings=4, max_trades=1)
        self.assertTrue(out.get("success"))
        self.assertIn("seed", out)
        self.assertIn("trade", out)


if __name__ == "__main__":
    unittest.main()
