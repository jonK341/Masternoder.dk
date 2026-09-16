"""Unit tests for signal stack + agent profit learning."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch


class TestSignalStackScoring(unittest.TestCase):
    def test_score_search_hit_composite(self):
        from backend.services.exchange_signal_stack_service import score_search_hit

        hit = {
            "symbol": "DOGE",
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "search_score": 20.0,
            "avg_net_bps": 18.0,
        }
        agent = {
            "skills": ["spatial_arbitrage", "kelly_sizing"],
            "skill_proficiency": {"spatial_arbitrage": 0.4, "kelly_sizing": 0.3},
        }
        row = score_search_hit(hit, skill_ids=agent["skills"], agent=agent)
        self.assertEqual(row["symbol"], "DOGE")
        self.assertGreater(float(row.get("composite_score") or 0), 0)
        self.assertIn("ai_score", row)

    def test_enrich_pair_search_for_ai_merges_hot(self):
        from backend.services.exchange_signal_stack_service import enrich_pair_search_for_ai

        syms, ranked = enrich_pair_search_for_ai(
            hot_symbols=["BTC"],
            pair_search={
                "success": True,
                "hot_symbols": ["ETH", "BTC"],
                "hits": [{"symbol": "SOL", "buy_venue": "a", "sell_venue": "b", "search_score": 10, "net_bps": 12}],
            },
            base_symbols=["XRP"],
        )
        self.assertIn("BTC", syms)
        self.assertIn("ETH", syms)
        self.assertIn("XRP", syms)


class TestAgentProfitLearning(unittest.TestCase):
    def test_apply_profit_learning_updates_proficiency(self):
        from backend.services.exchange_agent_profit_learning_service import apply_profit_learning

        acct = {"agent_id": "test_agent", "skills": ["spatial_arbitrage"], "skill_proficiency": {}}
        res = apply_profit_learning(acct, 2.5, agent_id="test_agent")
        self.assertTrue(res.get("success"))
        self.assertIn("learning", res)
        self.assertGreater(float(acct.get("skill_proficiency", {}).get("spatial_arbitrage") or 0), 0)


class TestSignalStackEnabled(unittest.TestCase):
    def test_enabled_env_override(self):
        from backend.services import exchange_signal_stack_service as ss

        with patch.dict(os.environ, {"EXCHANGE_SIGNAL_STACK": "1"}):
            self.assertTrue(ss.enabled())


if __name__ == "__main__":
    unittest.main()
