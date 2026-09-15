#!/usr/bin/env python3
"""Agent-to-agent MN2 peer mesh."""
import os
import sys
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


class TestAgentPeerTransactions(unittest.TestCase):
    def test_discover_mesh_agents_includes_defaults(self):
        from backend.services.agent_peer_transactions_service import discover_mesh_agents
        agents = discover_mesh_agents()
        ids = {a["agent_id"] for a in agents}
        self.assertIn("monitoring_agent", ids)
        self.assertIn("mn2_scout", ids)
        self.assertGreaterEqual(len(agents), 10)

    def test_directed_pairs_count(self):
        from backend.services.agent_peer_transactions_service import _directed_pairs
        pairs = _directed_pairs(["a", "b", "c"])
        self.assertEqual(len(pairs), 6)

    def test_mesh_dry_run(self):
        from backend.services.agent_peer_transactions_service import run_agent_peer_mesh
        fake_agents = [
            {"agent_id": "agent_a", "user_id": "agent:agent_a", "address": "addr_a"},
            {"agent_id": "agent_b", "user_id": "agent:agent_b", "address": "addr_b"},
        ]
        with patch(
            "backend.services.agent_peer_transactions_service.discover_mesh_agents",
            return_value=fake_agents,
        ), patch(
            "backend.services.agent_peer_transactions_service._resolve_addresses",
            return_value=fake_agents,
        ):
            res = run_agent_peer_mesh(max_txs=2, dry_run=True)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("agents"), 2)
        self.assertGreaterEqual(len(res.get("transfers") or []), 1)

    def test_mesh_needs_two_agents(self):
        from backend.services.agent_peer_transactions_service import run_agent_peer_mesh
        one = [{"agent_id": "solo", "user_id": "agent:solo", "address": "x"}]
        with patch(
            "backend.services.agent_peer_transactions_service.discover_mesh_agents",
            return_value=one,
        ), patch(
            "backend.services.agent_peer_transactions_service._resolve_addresses",
            return_value=one,
        ):
            res = run_agent_peer_mesh(max_txs=2, dry_run=False)
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("skipped_reason"), "need_at_least_two_agents_with_addresses")


if __name__ == "__main__":
    unittest.main()
