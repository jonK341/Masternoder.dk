#!/usr/bin/env python3
"""Shop agent finish-move tick (dry run)."""
import os
import sys
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


class TestAgentShopTick(unittest.TestCase):
    def test_dry_run_records_purchases_without_wallet_call(self):
        from backend.services import agent_shop_tick_service as tick

        items = [{"id": "boost-small", "name": "Small boost", "price": 5}]
        users = [{"user_id": "u1", "agent_id": "mn2_scout"}]
        with patch.object(tick, "_cheap_coin_items", return_value=items):
            with patch.object(tick, "_bound_agent_users", return_value=users):
                with patch(
                    "backend.services.shop_mn2_purchase_core.purchase_with_mn2_balance"
                ) as purchase:
                    out = tick.run_agent_shop_tick(dry_run=True, max_purchases=2)
        purchase.assert_not_called()
        self.assertTrue(out.get("success"))
        self.assertEqual(out.get("purchases"), 1)
        self.assertTrue(out.get("dry_run"))
        self.assertEqual(out["results"][0]["item_id"], "boost-small")


if __name__ == "__main__":
    unittest.main()
