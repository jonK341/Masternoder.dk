#!/usr/bin/env python3
"""
Unit tests for backend/services/mn2_staking_service.py.

Uses a temp data dir and an in-memory points store so no app/daemon/files are touched.
Run: pytest tests/unit/test_mn2_staking.py -v
"""
import os
import sys
import json
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import backend.services.mn2_staking_service as staking


class FakePoints:
    def __init__(self):
        self.store = {}

    def add_points(self, uid, pt, amt, source=None, metadata=None):
        self.store.setdefault(uid, {}).setdefault(pt, 0.0)
        self.store[uid][pt] += float(amt)
        return {"success": True}

    def get_all_points(self, uid):
        s = self.store.get(uid, {})
        pts = {
            "mn2_balance": float(s.get("mn2_balance", 0.0)),
            "mn2_staked": float(s.get("mn2_staked", 0.0)),
            "systems": dict(s),
        }
        return {"success": True, "points": pts}

    def get_game_time_and_boosters(self, uid):
        return {"active_boosters": [], "game_time_remaining_minutes": 0}


class StakingTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Redirect all state + config to the temp dir
        self._orig_data_dir = staking._data_dir
        staking._data_dir = lambda: self.tmp
        # Minimal config controlling test behavior
        with open(os.path.join(self.tmp, "mn2_staking_config.json"), "w", encoding="utf-8") as f:
            json.dump({
                "enabled": True,
                "min_stake": 0.1,
                "max_stake_per_user": 1000,
                "instant_unstake": True,
                "base_apr_percent": 10.0,
                "reward_pool_mode": "realized_yield",
                "site_margin_percent": 20.0,
                "accrual_interval_minutes": 60,
                "requires_verification": False,
                "terms_version": "1.0",
                "worker": {"uptime_weight": 1.25, "min_uptime_weight": 1.0, "max_uptime_weight": 1.5,
                           "heartbeat_interval_seconds": 30, "grace_missed_heartbeats": 2, "uptime_window_minutes": 60},
                "longevity_tiers": [{"id": "bronze", "min_days": 0, "multiplier": 1.0, "label": "Bronze"}],
                "boost": {"shop_effect": "staking_boost", "max_stacked_multiplier": 2.0},
                "auto_compound": {"enabled_default": False, "min_reward_to_compound": 0.01},
                "dynamic_apr": {"enabled": False, "target_total_staked": 1000000, "min_apr_percent": 2.0, "max_apr_percent": 8.0},
                "stabilization_reserve": {"enabled": True, "fund_from_margin_percent": 25.0, "max_reserve_mn2": 50000},
                "streak": {"enabled": True, "per_day_bonus": 0.01, "max_bonus": 0.1, "merged_into_longevity": True},
            }, f)
        self.fake = FakePoints()
        self._orig_points = staking._points
        staking._points = lambda: self.fake
        # Keep the real append-only ledger (separate data dir) out of unit tests
        self._orig_ledger = staking._ledger_append
        staking._ledger_append = lambda *a, **k: None

    def tearDown(self):
        staking._data_dir = self._orig_data_dir
        staking._points = self._orig_points
        staking._ledger_append = self._orig_ledger

    def _credit(self, uid, amount):
        self.fake.add_points(uid, "mn2_balance", amount)


class TestStakeUnstake(StakingTestBase):
    def test_consent_required_before_staking(self):
        self._credit("u1", 10)
        res = staking.stake("u1", 5)
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("code"), "consent_required")

    def test_stake_moves_balance_to_staked(self):
        self._credit("u1", 10)
        staking.accept_terms("u1")
        res = staking.stake("u1", 4)
        self.assertTrue(res.get("success"), res)
        bal, staked = staking.get_balances("u1")
        self.assertAlmostEqual(bal, 6.0, places=6)
        self.assertAlmostEqual(staked, 4.0, places=6)

    def test_cannot_stake_more_than_balance(self):
        self._credit("u1", 2)
        staking.accept_terms("u1")
        res = staking.stake("u1", 5)
        self.assertFalse(res.get("success"))

    def test_below_min_stake_rejected(self):
        self._credit("u1", 10)
        staking.accept_terms("u1")
        res = staking.stake("u1", 0.01)
        self.assertFalse(res.get("success"))

    def test_instant_unstake_returns_balance(self):
        self._credit("u1", 10)
        staking.accept_terms("u1")
        staking.stake("u1", 6)
        res = staking.unstake("u1", 4)
        self.assertTrue(res.get("success"), res)
        bal, staked = staking.get_balances("u1")
        self.assertAlmostEqual(bal, 8.0, places=6)
        self.assertAlmostEqual(staked, 2.0, places=6)

    def test_cannot_unstake_more_than_staked(self):
        self._credit("u1", 10)
        staking.accept_terms("u1")
        staking.stake("u1", 3)
        res = staking.unstake("u1", 5)
        self.assertFalse(res.get("success"))

    def test_full_unstake_resets_longevity(self):
        self._credit("u1", 10)
        staking.accept_terms("u1")
        staking.stake("u1", 5)
        staking.unstake("u1", 5)
        st = staking.get_stake("u1")
        self.assertEqual(st["staked"], 0.0)
        self.assertEqual(st["longevity_days"], 0.0)


class TestCalculatorAndStatus(StakingTestBase):
    def test_estimate_rewards_positive(self):
        out = staking.estimate_rewards(amount=100, days=365, uptime=1.0, boost=1.0)
        self.assertTrue(out["success"])
        self.assertGreater(out["projected_reward_mn2"], 0)

    def test_status_fields(self):
        self._credit("u1", 10)
        staking.accept_terms("u1")
        staking.stake("u1", 5)
        st = staking.get_stake("u1")
        for key in ("staked", "apr_percent", "longevity_tier", "multipliers",
                    "estimated_next_interval_reward", "terms_accepted", "instant_unstake"):
            self.assertIn(key, st)
        self.assertTrue(st["terms_accepted"])


class TestAccrual(StakingTestBase):
    def test_accrual_credits_apr_fallback(self):
        # No daemon -> realized yield 0 -> APR fallback path
        self._credit("u1", 100)
        staking.accept_terms("u1")
        staking.stake("u1", 100)
        before, _ = staking.get_balances("u1")
        res = staking.accrue_rewards(force=True)
        self.assertTrue(res.get("success"), res)
        self.assertEqual(res.get("source"), "apr_fallback")
        self.assertGreaterEqual(res.get("rewarded_users"), 1)
        after, _ = staking.get_balances("u1")
        self.assertGreater(after, before)

    def test_accrual_idempotent_per_interval(self):
        self._credit("u1", 100)
        staking.accept_terms("u1")
        staking.stake("u1", 100)
        staking.accrue_rewards(force=True)
        res2 = staking.accrue_rewards(force=False)
        self.assertTrue(res2.get("skipped"))

    def test_realized_yield_counts_each_coinstake_once(self):
        # Daemon coinstake txns persist in listtransactions across intervals; each txid
        # must contribute to realized yield only once (no re-counting / over-distribution).
        import backend.services.mn2_rpc_client as rpc
        orig = rpc.listtransactions
        rpc.listtransactions = lambda count=200, skip=0: {
            "error": None,
            "result": [
                {"category": "stake", "amount": 2.0, "txid": "stake-aaa"},
                {"category": "generate", "amount": 1.0, "txid": "gen-bbb"},
            ],
        }
        try:
            self._credit("u1", 100)
            staking.accept_terms("u1")
            staking.stake("u1", 100)

            r1 = staking.accrue_rewards(force=True)
            self.assertEqual(r1.get("source"), "realized_yield")
            self.assertAlmostEqual(r1.get("realized_yield_mn2"), 3.0, places=6)

            # Same coinstake txns still returned next interval -> must not be counted again.
            r2 = staking.accrue_rewards(force=True)
            self.assertEqual(r2.get("realized_yield_mn2"), 0.0)
            self.assertEqual(r2.get("source"), "apr_fallback")
        finally:
            rpc.listtransactions = orig

    def test_rewards_table_records_rows(self):
        self._credit("u1", 100)
        staking.accept_terms("u1")
        staking.stake("u1", 100)
        staking.accrue_rewards(force=True)
        table = staking.get_rewards_table("u1")
        self.assertTrue(table["success"])
        self.assertGreaterEqual(len(table["rows"]), 1)
        self.assertGreater(table["summary"]["total_earned_mn2"], 0)

    def test_monitor_aggregates(self):
        for uid in ("u1", "u2"):
            self._credit(uid, 50)
            staking.accept_terms(uid)
            staking.stake(uid, 50)
        mon = staking.get_staking_monitor()
        self.assertTrue(mon["success"])
        self.assertEqual(mon["aggregates"]["active_stakers"], 2)
        self.assertAlmostEqual(mon["aggregates"]["total_staked"], 100.0, places=6)
        # display ids are anonymized
        for p in mon["processes"]:
            self.assertTrue(p["display_id"].startswith("user_"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
