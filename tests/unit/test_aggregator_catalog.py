"""Tests for aggregator hub v2 catalog API."""
import unittest

from backend.services.aggregator_catalog_service import (
    assign_agent,
    fulfillment_section,
    list_catalog,
    progress_snapshot,
    top25_list,
)


class TestAggregatorCatalog(unittest.TestCase):
    def test_catalog_has_75(self):
        r = list_catalog(limit=200)
        self.assertTrue(r["success"])
        self.assertEqual(r["count"], 75)
        first = r["aggregators"][0]
        self.assertTrue(first.get("skill_set"))
        self.assertEqual(first.get("status"), "active")

    def test_top25(self):
        r = top25_list()
        self.assertTrue(r["success"])
        self.assertEqual(r["count"], 25)
        self.assertEqual(r["aggregators"][0]["rank"], 1)

    def test_fulfillment(self):
        r = fulfillment_section()
        self.assertTrue(r["success"])
        self.assertTrue(len(r.get("playbook") or []) >= 3)

    def test_assign_and_progress(self):
        r = assign_agent("test_agg_user_v2", "agg_001", "agent_intelligence_01", chain_burst=2)
        self.assertTrue(r["success"])
        self.assertEqual(r["agent_status"], "active")
        self.assertTrue(r.get("skill_set"))
        p = progress_snapshot("test_agg_user_v2")
        self.assertTrue(p["success"])
        self.assertGreaterEqual(p["assigned_count"], 1)


if __name__ == "__main__":
    unittest.main()
