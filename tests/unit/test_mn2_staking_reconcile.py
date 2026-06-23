#!/usr/bin/env python3
"""
Unit tests for backend/services/mn2_staking_reconcile_service.py.

Builds fixture stores in a temp data dir (no app/daemon/files touched) and asserts
the conservation invariant passes when books balance and flags hard drift otherwise.
Run: pytest tests/unit/test_mn2_staking_reconcile.py -v
"""
import os
import sys
import json
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import backend.services.mn2_staking_reconcile_service as recon


class ReconcileTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "data"), exist_ok=True)
        self._orig = recon._base_dir
        recon._base_dir = lambda: self.tmp

    def tearDown(self):
        recon._base_dir = self._orig

    def _write(self, name, obj):
        with open(os.path.join(self.tmp, "data", name), "w", encoding="utf-8") as f:
            if name.endswith(".jsonl"):
                for row in obj:
                    f.write(json.dumps(row) + "\n")
            else:
                json.dump(obj, f)

    def _ledger(self, entries):
        self._write("mn2_ledger.json", {"entries": entries})


class TestBalanced(ReconcileTestBase):
    def test_all_checks_pass_when_books_balance(self):
        # 10 staked = 12 stake - 2 unstake; rewards rows 1.5 == staking_reward 1.5
        self._ledger([
            {"type": "stake", "amount": 12.0},
            {"type": "unstake", "amount": 2.0},
            {"type": "staking_reward", "amount": 1.5},
            {"type": "onramp_purchase", "amount": 50.0},
            {"type": "p2p_sell_escrow", "amount": 30.0},
            {"type": "p2p_buy", "amount": 20.0},
            {"type": "p2p_escrow_return", "amount": 0.0},
        ])
        self._write("mn2_stakes.json", {"u1": {"staked": 7.0}, "u2": {"staked": 3.0}})
        self._write("mn2_staking_rewards.jsonl", [{"reward_mn2": 1.0}, {"reward_mn2": 0.5}])
        self._write("mn2_onramp_orders.json", {"o1": {"status": "held", "mn2_amount": 50.0}})
        # outstanding escrow = 30 escrowed - 0 returned - 20 delivered = 10
        self._write("mn2_p2p_listings.json", {"l1": {"status": "open", "mn2_available": 6.0, "mn2_reserved": 4.0}})
        self._write("mn2_staking_reserve.json", {"reserve_mn2": 5.0, "lifetime_paid": 1.5, "lifetime_realized_yield": 0.0})

        rep = recon.reconcile()
        self.assertTrue(rep["ok"], rep["failed_checks"])
        self.assertEqual(rep["failed_checks"], [])

    def test_empty_stores_are_balanced(self):
        rep = recon.reconcile()
        self.assertTrue(rep["ok"])


class TestDrift(ReconcileTestBase):
    def test_staked_drift_flagged(self):
        self._ledger([{"type": "stake", "amount": 5.0}])  # ledger says 5 staked
        self._write("mn2_stakes.json", {"u1": {"staked": 9.0}})  # live says 9 -> drift 4
        rep = recon.reconcile()
        self.assertFalse(rep["ok"])
        self.assertIn("staked_matches_ledger", rep["failed_checks"])

    def test_reward_rows_drift_flagged(self):
        self._ledger([{"type": "staking_reward", "amount": 2.0}])
        self._write("mn2_staking_rewards.jsonl", [{"reward_mn2": 5.0}])  # rows say 5 -> drift 3
        rep = recon.reconcile()
        self.assertFalse(rep["ok"])
        self.assertIn("rewards_rows_match_ledger", rep["failed_checks"])

    def test_p2p_escrow_drift_flagged(self):
        self._ledger([{"type": "p2p_sell_escrow", "amount": 30.0}])  # expected outstanding 30
        self._write("mn2_p2p_listings.json", {"l1": {"status": "open", "mn2_available": 1.0, "mn2_reserved": 0.0}})
        rep = recon.reconcile()
        self.assertFalse(rep["ok"])
        self.assertIn("p2p_escrow_conservation", rep["failed_checks"])


if __name__ == "__main__":
    unittest.main()
