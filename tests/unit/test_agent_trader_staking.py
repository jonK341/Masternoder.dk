"""Trader agent staking pool bootstrap tests."""
import json
import os
import pytest

from tests.unit.test_mn2_staking import StakingTestBase
import backend.services.mn2_staking_service as staking
import backend.services.agent_wallet_service as aw
import backend.services.mn2_staking_agents_service as agents_svc
import backend.services.mn2_copy_trading as ct


class TraderStakingBase(StakingTestBase):
    def setUp(self):
        super().setUp()
        cfg_path = os.path.join(self.tmp, "mn2_staking_config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["trader_agents"] = {
            "enabled": True,
            "target_stake_mn2": 25000,
            "stake_variance_mn2": 10000,
            "keep_balance_min_mn2": 5000,
            "max_stake_per_user_override": 50000,
        }
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        wallets_path = os.path.join(self.tmp, "agent_wallets.json")
        wallets = {
            "agents": {
                "trader_agent_1": {"mn2_balance": 100000.0},
                "trader_agent_2": {"mn2_balance": 100000.0},
            },
        }
        with open(wallets_path, "w", encoding="utf-8") as f:
            json.dump(wallets, f)
        self._orig_wallets = aw._WALLETS_FILE
        aw._WALLETS_FILE = wallets_path

        treasury_path = os.path.join(self.tmp, "agent_treasury.json")
        with open(treasury_path, "w", encoding="utf-8") as f:
            json.dump({"trader_agent_count": 2, "per_agent_mn2": 100000}, f)
        self._orig_treasury = aw._TREASURY_FILE
        aw._TREASURY_FILE = treasury_path

        agents_path = os.path.join(self.tmp, "agent_staking_agents.json")
        with open(agents_path, "w", encoding="utf-8") as f:
            json.dump({"agents": {}}, f)
        self._orig_agents = agents_svc._AGENTS_FILE
        agents_svc._AGENTS_FILE = agents_path

        self._orig_follows = ct._FOLLOWS
        self._orig_log = ct._LOG
        ct._FOLLOWS = os.path.join(self.tmp, "copy_trading.json")
        ct._LOG = os.path.join(self.tmp, "copy_trading.jsonl")

    def tearDown(self):
        aw._WALLETS_FILE = self._orig_wallets
        aw._TREASURY_FILE = self._orig_treasury
        agents_svc._AGENTS_FILE = self._orig_agents
        ct._FOLLOWS = self._orig_follows
        ct._LOG = self._orig_log
        super().tearDown()


def test_target_stake_variance():
    t = TraderStakingBase()
    t.setUp()
    try:
        from backend.services.agent_trader_staking_service import target_stake_for_agent

        t1 = target_stake_for_agent("trader_agent_1")
        t2 = target_stake_for_agent("trader_agent_2")
        assert 15000 <= t1 <= 35000
        assert 15000 <= t2 <= 35000
    finally:
        t.tearDown()


def test_join_pool_stakes_traders():
    t = TraderStakingBase()
    t.setUp()
    try:
        from backend.services.agent_trader_staking_service import join_trader_agents_to_pool

        r = join_trader_agents_to_pool(dry_run=False)
        assert r.get("success") is True
        assert r.get("total_staked_mn2", 0) > 0
        st = staking.get_stake("trader_agent_1")
        assert float(st.get("staked") or 0) >= 15000
    finally:
        t.tearDown()


def test_mirror_leader_reward():
    t = TraderStakingBase()
    t.setUp()
    try:
        from backend.services.agent_trader_staking_service import join_trader_agents_to_pool

        join_trader_agents_to_pool(dry_run=False)
        staking.accept_terms("follower_user")
        t.fake.add_points("follower_user", "mn2_balance", 1000.0)
        ct.upsert_follower("follower_user", "trader_agent_1", scale=0.5, max_mn2_per_step=100)
        out = ct.mirror_leader_reward("trader_agent_1", 10.0, interval_id="test-int")
        assert out.get("success") is True
        assert out.get("mirrored") == 1
        st = staking.get_stake("follower_user")
        assert float(st.get("total_earned") or 0) == pytest.approx(5.0)
    finally:
        t.tearDown()
