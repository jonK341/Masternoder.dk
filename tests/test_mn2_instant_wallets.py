#!/usr/bin/env python3
"""Tests for instant MN2 rewards, multi-wallet, profile monitor, and settlement."""
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


class TestMN2WalletService(unittest.TestCase):
    def test_create_additional_wallet(self):
        import tempfile
        from backend.services import mn2_wallet_service as ws

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mn2_user_addresses.json")
            with patch.object(ws, "_addresses_path", return_value=path):
                with patch.object(ws, "_data_dir", return_value=tmp):
                    with patch.object(ws, "_generate_valid_address", return_value={"success": True, "deposit_address": "MxTest123"}):
                        res = ws.create_additional_wallet("user_a", label="savings")
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("deposit_address"), "MxTest123")
            self.assertEqual(res.get("label"), "savings")

    def test_seed_pool_addresses(self):
        import tempfile
        from backend.services import mn2_wallet_service as ws

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mn2_user_addresses.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"user_a": "MxPrimary"}, f)
            with patch.object(ws, "_addresses_path", return_value=path):
                with patch.object(ws, "_data_dir", return_value=tmp):
                    res = ws.seed_pool_addresses(["MxPool1", "MxPool2", "MxPrimary"])
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("count"), 2)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("pool_1"), "MxPool1")
            self.assertEqual(data.get("pool_2"), "MxPool2")

    def test_pool_assign_creates_full_wallet_dict(self):
        import tempfile
        from backend.services import mn2_wallet_service as ws

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mn2_user_addresses.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"pool_1": "MxPoolAddr"}, f)
            with patch.object(ws, "_addresses_path", return_value=path):
                with patch.object(ws, "_data_dir", return_value=tmp):
                    with patch.object(ws, "_address_validity", return_value=True):
                        res = ws.get_or_create_deposit_address("user_new")
            self.assertTrue(res.get("success"))
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            entry = data.get("user_new")
            self.assertIsInstance(entry, dict)
            self.assertEqual(entry.get("primary"), "MxPoolAddr")
            self.assertEqual(entry.get("wallet_type"), "core")
            self.assertTrue(entry.get("addresses"))

    def test_ensure_user_wallet_upgrades_legacy_string(self):
        import tempfile
        from backend.services import mn2_wallet_service as ws

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mn2_user_addresses.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"legacy_user": "MxLegacyAddr"}, f)
            with patch.object(ws, "_addresses_path", return_value=path):
                with patch.object(ws, "_data_dir", return_value=tmp):
                    with patch.object(ws, "_address_validity", return_value=True):
                        res = ws.ensure_user_wallet("legacy_user")
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("deposit_address"), "MxLegacyAddr")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertIsInstance(data["legacy_user"], dict)

    def test_normalize_all_legacy_wallets(self):
        import tempfile
        from backend.services import mn2_wallet_service as ws

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mn2_user_addresses.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"u1": "Mx1", "u2": {"primary": "Mx2", "wallet_type": "core", "addresses": []}}, f)
            with patch.object(ws, "_addresses_path", return_value=path):
                with patch.object(ws, "_data_dir", return_value=tmp):
                    res = ws.normalize_all_legacy_wallets()
            self.assertEqual(res.get("upgraded"), 1)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertIsInstance(data["u1"], dict)

    def test_create_additional_wallet_pool_fallback(self):
        import tempfile
        from backend.services import mn2_wallet_service as ws

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mn2_user_addresses.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"pool_1": "MxPoolAddr", "user_a": "MxPrimary"}, f)
            with patch.object(ws, "_addresses_path", return_value=path):
                with patch.object(ws, "_data_dir", return_value=tmp):
                    with patch.object(ws, "_generate_valid_address", return_value={"success": False, "error": "rpc down"}):
                        with patch.object(ws, "_address_validity", return_value=True):
                            res = ws.create_additional_wallet("user_a", label="backup")
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("deposit_address"), "MxPoolAddr")


class TestMN2LedgerRewards(unittest.TestCase):
    def test_reward_types_count_as_inflow(self):
        from backend.services.mn2_ledger import get_wallet_activity_days
        import tempfile
        from backend.services import mn2_ledger as led

        entries = [
            {
                "user_id": "u1",
                "type": "battle_crypto_claim",
                "amount": 0.25,
                "created_at": "2026-09-15T12:00:00Z",
                "metadata": {},
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "mn2_ledger.json")
            with open(path, "w") as f:
                json.dump({"entries": entries}, f)
            with patch.object(led, "_ledger_path", return_value=path):
                buckets = get_wallet_activity_days("u1", days=5)
        self.assertTrue(any(b.get("deposits_mn2", 0) > 0 for b in buckets))


class TestCreditMn2Instant(unittest.TestCase):
    @patch("backend.services.activity_events_service.emit")
    @patch("backend.services.mn2_ledger.append_entry")
    @patch("backend.services.mn2_earn_auth.require_earn_user", return_value=(True, "u1"))
    @patch("backend.services.mn2_chain_rewards_service.chain_payouts_enabled", return_value=False)
    def test_credit_mn2_instant(self, _chain, _earn, mock_append, _emit):
        from backend.services.game_mn2_rewards import credit_mn2

        mock_db = MagicMock()
        mock_db.add_points.return_value = {"success": True}
        with patch.dict("sys.modules", {"backend.services.unified_points_database": MagicMock(unified_points_db=mock_db)}):
            with patch("backend.services.unified_points_database.unified_points_db", mock_db, create=True):
                res = credit_mn2("u1", 0.01, source="test_reward", reference="ref-1")
        self.assertTrue(res.get("success"))
        self.assertTrue(res.get("instant"))
        mock_append.assert_called_once()


class TestSettlementService(unittest.TestCase):
    def test_settlement_dry_run_structure(self):
        from backend.services.agent_mn2_settlement_service import run_mn2_ecosystem_settlement

        with patch("backend.services.agent_mn2_settlement_service._test_daemon", return_value={"healthy": True, "health": {"block_height": 1}}):
            with patch("backend.services.agent_mn2_settlement_service._settle_battle_crypto", return_value={"claims": 0, "users": 0, "errors": []}):
                with patch("backend.services.agent_mn2_settlement_service._scan_chain_payout_queue", return_value={"payouts": 0, "skipped": 0, "errors": []}):
                    with patch("backend.services.mn2_deposit_scanner.run_scanner", return_value={"success": True, "credits_applied": 0}):
                        with patch("backend.services.mn2_masternode_service.rented_masternodes_snapshot", return_value={"success": True, "rented_count": 0}):
                            res = run_mn2_ecosystem_settlement(systems=["all"], dry_run=True)
        self.assertTrue(res.get("success"))
        self.assertIn("battle", res.get("results", {}))

    def test_settle_reconcile_uses_ok_field(self):
        from backend.services.agent_mn2_settlement_service import _settle_reconcile

        with patch(
            "backend.services.mn2_staking_reconcile_service.reconcile",
            return_value={"success": True, "ok": False, "failed_checks": ["staked_matches_ledger"]},
        ):
            res = _settle_reconcile()
        self.assertFalse(res.get("ok"))

    def test_daemon_probe_never_raises(self):
        from backend.services.mn2_daemon_health_service import probe_daemon

        with patch(
            "backend.services.mn2_rpc_client.health_check",
            return_value={"status": "healthy", "block_height": 12345},
        ):
            res = probe_daemon(extended=False)
        self.assertTrue(res.get("healthy"))


class TestAgentCronPresets(unittest.TestCase):
    def test_mn2_fast_preset(self):
        from backend.services.agent_cron_service import expand_preset

        self.assertEqual(expand_preset("mn2_fast"), ["mn2_ecosystem_settlement_fast"])
        self.assertEqual(expand_preset("mn2_transactions"), ["mn2_ecosystem_settlement"])
        self.assertEqual(expand_preset("mn2_game"), ["mn2_game_systems"])


class TestProfileMonitor(unittest.TestCase):
    def test_last_settlement_snapshot_empty(self):
        from backend.routes.mn2_routes import _last_settlement_snapshot
        snap = _last_settlement_snapshot()
        self.assertIsInstance(snap, dict)


if __name__ == "__main__":
    unittest.main()
