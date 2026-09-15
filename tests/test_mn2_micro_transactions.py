#!/usr/bin/env python3
"""MN2 micro-transaction burst service."""
import os
import sys
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


class TestMn2MicroTransactions(unittest.TestCase):
    def test_micro_config_defaults(self):
        from backend.services.mn2_micro_transactions_service import micro_config
        cfg = micro_config()
        self.assertTrue(cfg["enabled"])
        self.assertGreater(cfg["amount_mn2"], 0)
        self.assertGreaterEqual(cfg["max_per_run"], 1)

    def test_split_amount_parts(self):
        from backend.services.mn2_micro_transactions_service import _split_amount
        parts = _split_amount(0.00002, 2)
        self.assertEqual(len(parts), 2)
        self.assertAlmostEqual(sum(parts), 0.00002, places=8)

    def test_burst_dry_run(self):
        from backend.services.mn2_micro_transactions_service import run_micro_transaction_burst
        with patch(
            "backend.services.agent_mn2_settlement_service._discover_active_user_ids",
            return_value=["user_a", "user_b"],
        ):
            res = run_micro_transaction_burst(max_txs=4, dry_run=True, user_ids=["user_a"])
        self.assertTrue(res.get("success"))
        self.assertGreaterEqual(res.get("attempted", 0), 1)

    def test_burst_disabled_when_chain_off(self):
        from backend.services.mn2_micro_transactions_service import run_micro_transaction_burst
        with patch(
            "backend.services.mn2_micro_transactions_service.micro_config",
            return_value={
                "enabled": True,
                "amount_mn2": 0.00001,
                "max_per_run": 5,
                "max_per_user_per_day": 10,
                "split_parts": 1,
                "actions": ["activity_tick"],
                "chain_enabled": False,
                "min_chain_mn2": 0.00001,
            },
        ):
            res = run_micro_transaction_burst(max_txs=2, dry_run=False)
        self.assertEqual(res.get("skipped_reason"), "chain_reward_payouts_disabled")


if __name__ == "__main__":
    unittest.main()
