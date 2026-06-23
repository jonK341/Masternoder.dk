#!/usr/bin/env python3
"""
Unit tests for backend/services/mn2_staking_agents_service.py (autonomous personas).

Reuses the isolated temp-dir + FakePoints harness from test_mn2_staking so no app,
daemon, real data files, or ledger are touched.
Run: pytest tests/unit/test_mn2_staking_agents.py -v
"""
import os
import sys
import json
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from tests.unit.test_mn2_staking import StakingTestBase
import backend.services.mn2_staking_service as staking
import backend.services.mn2_staking_agents_service as agents


class AgentBase(StakingTestBase):
    def _agent(self, agent_id, user_id, **policy):
        return agents.upsert_agent(agent_id, user_id, policy=policy)


class TestConsentGate(AgentBase):
    def test_blocked_without_consent(self):
        self._credit("u1", 100)
        self._agent("a1", "u1", target_staked=10, auto_accept_terms=False)
        r = agents.run_agent("a1")
        self.assertFalse(r.get("success"))
        self.assertEqual(r.get("code"), "consent_required")

    def test_auto_accept_then_stakes_to_target(self):
        self._credit("u1", 100)
        self._agent("a1", "u1", target_staked=10, auto_accept_terms=True)
        r = agents.run_agent("a1")
        self.assertTrue(r.get("success"), r)
        _, staked = staking.get_balances("u1")
        self.assertAlmostEqual(staked, 10.0, places=6)


class TestRebalance(AgentBase):
    def setUp(self):
        super().setUp()
        self._credit("u1", 100)
        staking.accept_terms("u1")

    def test_stake_toward_target_respects_keep_balance_min(self):
        self._agent("a1", "u1", target_staked=100, keep_balance_min=30)
        agents.run_agent("a1")
        bal, staked = staking.get_balances("u1")
        self.assertAlmostEqual(staked, 70.0, places=6)
        self.assertAlmostEqual(bal, 30.0, places=6)

    def test_unstake_when_over_max(self):
        staking.stake("u1", 80)
        self._agent("a1", "u1", target_staked=80, max_staked=50)
        agents.run_agent("a1")
        _, staked = staking.get_balances("u1")
        self.assertAlmostEqual(staked, 50.0, places=6)

    def test_step_max_caps_single_move(self):
        self._agent("a1", "u1", target_staked=100, rebalance_step_max=15)
        agents.run_agent("a1")
        _, staked = staking.get_balances("u1")
        self.assertAlmostEqual(staked, 15.0, places=6)

    def test_dry_run_changes_nothing(self):
        self._agent("a1", "u1", target_staked=50)
        r = agents.run_agent("a1", dry_run=True)
        self.assertTrue(r.get("dry_run"))
        _, staked = staking.get_balances("u1")
        self.assertAlmostEqual(staked, 0.0, places=6)


class TestMonitorAndKillSwitch(AgentBase):
    def test_managed_flag_and_monitor_counts(self):
        self._credit("u1", 100)
        staking.accept_terms("u1")
        self._agent("a1", "u1", target_staked=40, auto_accept_terms=True)
        agents.run_agent("a1")
        mon = staking.get_staking_monitor()
        agg = mon["aggregates"]
        self.assertEqual(agg["agent_managed_stakers"], 1)
        self.assertAlmostEqual(agg["agent_staked_mn2"], 40.0, places=6)
        self.assertGreaterEqual(agg["agent_actions_24h"], 1)
        self.assertTrue(any(p.get("agent_managed") for p in mon["processes"]))

    def test_kill_switch_disables_automation(self):
        # rewrite config with the ops kill switch off
        with open(os.path.join(self.tmp, "mn2_staking_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["agent"] = {"automation_enabled": False}
        with open(os.path.join(self.tmp, "mn2_staking_config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        self._credit("u1", 100)
        staking.accept_terms("u1")
        self._agent("a1", "u1", target_staked=10, auto_accept_terms=True)
        r = agents.run_agent("a1")
        self.assertFalse(r.get("success"))
        self.assertEqual(r.get("code"), "automation_disabled")


if __name__ == "__main__":
    unittest.main()
