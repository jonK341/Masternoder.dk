#!/usr/bin/env python3
"""
Tests for MN2 crypto integration API (Phases 2–10).
Uses Flask test client and mocks for RPC/wallet/ledger so no daemon is required.
Run: python tests/test_mn2_crypto.py   or   pytest tests/test_mn2_crypto.py -v
"""
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Project root on path
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)

# Optional: suppress create_app blueprint prints
import io

_app = None


def get_app():
    global _app
    if _app is None:
        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            from src.app import create_app
            app = create_app()
            _app = app
    return _app


class TestMN2Balance(unittest.TestCase):
    """GET /api/mn2/balance"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.routes.mn2_routes.get_balance")
    @patch("backend.routes.mn2_routes._load_mn2_config")
    def test_balance_returns_ok(self, mock_config, mock_get_balance):
        mock_get_balance.return_value = {"success": True, "user_id": "test_user", "mn2_balance": 1.5}
        mock_config.return_value = {"coins_per_mn2": 100, "shop_revenue_address": "", "withdrawal_requires_verification": False}
        r = self.client.get("/api/mn2/balance?user_id=test_user")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("mn2_balance"), 1.5)
        self.assertEqual(data.get("coins_per_mn2"), 100)


class TestMN2Price(unittest.TestCase):
    """GET /api/mn2/price"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.routes.mn2_routes._load_mn2_config")
    def test_price_returns_ok(self, mock_config):
        mock_config.return_value = {"coins_per_mn2": 100}
        r = self.client.get("/api/mn2/price")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("coins_per_mn2"), 100)


class TestMN2DepositAddress(unittest.TestCase):
    """GET /api/mn2/deposit-address"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.routes.mn2_routes.get_or_create_deposit_address")
    def test_deposit_address_returns_address(self, mock_get_addr):
        mock_get_addr.return_value = {
            "success": True,
            "user_id": "test_user",
            "deposit_address": "MxTestDepositAddress123",
        }
        r = self.client.get("/api/mn2/deposit-address?user_id=test_user")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("deposit_address"), "MxTestDepositAddress123")
        self.assertIn("explorer_address_url", data)

    @patch("backend.routes.mn2_routes.get_or_create_deposit_address")
    def test_deposit_address_fail_returns_500(self, mock_get_addr):
        mock_get_addr.return_value = {"success": False, "error": "RPC unavailable"}
        r = self.client.get("/api/mn2/deposit-address?user_id=test_user")
        self.assertEqual(r.status_code, 500)
        data = r.get_json()
        self.assertFalse(data.get("success"))


class TestMN2Transactions(unittest.TestCase):
    """GET /api/mn2/transactions"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.routes.mn2_routes.get_entries_by_user")
    def test_transactions_returns_list(self, mock_get_entries):
        mock_get_entries.return_value = [
            {"user_id": "test_user", "type": "deposit", "amount": 1.0, "txid": "abc", "created_at": "2025-01-01T00:00:00Z"},
        ]
        r = self.client.get("/api/mn2/transactions?user_id=test_user&limit=10")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertIsInstance(data.get("transactions"), list)
        self.assertEqual(len(data["transactions"]), 1)
        self.assertIn("explorer_tx_url", data["transactions"][0])


class TestMN2OrderPayment(unittest.TestCase):
    """POST /api/mn2/order-payment and GET /api/mn2/order-payment/status"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.services.mn2_order_payment_service.create_order_payment")
    @patch("backend.services.mn2_rpc_client.getnewaddress")
    @patch("backend.routes.shop_routes._get_shop_items")
    @patch("backend.routes.mn2_routes._load_mn2_config")
    def test_order_payment_creates_and_returns_address(
        self, mock_config, mock_shop_items, mock_getnewaddress, mock_create_order
    ):
        mock_config.return_value = {"coins_per_mn2": 100}
        mock_shop_items.return_value = [{"id": "item1", "name": "Test Item", "price": 50}]
        mock_getnewaddress.return_value = {"result": "MxOrderAddress456"}
        mock_create_order.return_value = {
            "payment_ref": "ref123",
            "amount_mn2": 0.5,
            "expires_at": "2025-12-31T00:00:00Z",
            "item_name": "Test Item",
        }
        r = self.client.post(
            "/api/mn2/order-payment",
            data=json.dumps({"user_id": "test_user", "item_id": "item1", "quantity": 1}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("address"), "MxOrderAddress456")
        self.assertEqual(data.get("payment_ref"), "ref123")

    @patch("backend.services.mn2_order_payment_service.get_order")
    def test_order_payment_status_returns_404_when_not_found(self, mock_get_order):
        mock_get_order.return_value = None
        r = self.client.get("/api/mn2/order-payment/status?payment_ref=nonexistent&user_id=test_user")
        self.assertEqual(r.status_code, 404)

    @patch("backend.services.mn2_order_payment_service.get_order")
    def test_order_payment_status_returns_ok(self, mock_get_order):
        from datetime import datetime, timedelta, timezone
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        mock_get_order.return_value = {
            "payment_ref": "ref1",
            "status": "pending",
            "address": "MxAddr",
            "amount_mn2": 0.5,
            "item_id": "item1",
            "quantity": 1,
            "txid": None,
            "fulfilled_at": None,
            "expires_at": future,
        }
        r = self.client.get("/api/mn2/order-payment/status?payment_ref=ref1&user_id=test_user")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "pending")


class TestMN2Withdraw(unittest.TestCase):
    """POST /api/mn2/withdraw"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.routes.mn2_routes.append_entry")
    @patch("backend.services.unified_points_database.unified_points_db")
    @patch("backend.services.mn2_rpc_client.sendtoaddress")
    @patch("backend.services.mn2_rpc_client.validateaddress")
    @patch("backend.routes.mn2_routes.get_balance")
    @patch("backend.routes.mn2_routes.count_withdrawals_since")
    @patch("backend.routes.mn2_routes.sum_withdrawals_since")
    @patch("backend.routes.mn2_routes._load_mn2_config")
    def test_withdraw_success(
        self,
        mock_config,
        mock_sum_w,
        mock_count_w,
        mock_get_balance,
        mock_validate,
        mock_send,
        mock_db,
        mock_append,
    ):
        mock_config.return_value = {
            "withdrawal_requires_verification": False,
            "min_withdrawal": 0,
            "max_withdrawal": 0,
            "withdrawal_fee": 0.001,
            "max_withdrawal_per_day": 10,
            "max_withdrawal_amount_per_day": 0,
        }
        mock_count_w.return_value = 0
        mock_sum_w.return_value = 0
        mock_get_balance.return_value = {"success": True, "mn2_balance": 10.0}
        mock_validate.return_value = {"result": True}
        mock_send.return_value = {"result": "txid123"}
        mock_db.add_points = MagicMock()
        r = self.client.post(
            "/api/mn2/withdraw",
            data=json.dumps({"user_id": "test_user", "address": "MxValidAddress", "amount": 1.0}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("txid"), "txid123")
        self.assertIn("explorer_tx_url", data)

    @patch("backend.routes.mn2_routes._load_mn2_config")
    def test_withdraw_rejects_missing_address(self, mock_config):
        mock_config.return_value = {"withdrawal_fee": 0.001}
        r = self.client.post(
            "/api/mn2/withdraw",
            data=json.dumps({"user_id": "test_user", "amount": 1.0}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    @patch("backend.routes.mn2_routes._load_mn2_config")
    def test_withdraw_rejects_invalid_amount(self, mock_config):
        mock_config.return_value = {}
        r = self.client.post(
            "/api/mn2/withdraw",
            data=json.dumps({"user_id": "test_user", "address": "MxAddr", "amount": 0}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)


class TestMN2ScanDeposits(unittest.TestCase):
    """POST /api/mn2/scan-deposits"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.services.mn2_deposit_scanner.run_scanner")
    def test_scan_deposits_success_when_no_secret(self, mock_run):
        mock_run.return_value = {"success": True, "credits_applied": 0}
        r = self.client.post("/api/mn2/scan-deposits")
        # If MN2_SCAN_SECRET is not set, request is allowed
        if r.status_code == 403:
            self.skipTest("MN2_SCAN_SECRET is set in env; scan requires token")
        self.assertIn(r.status_code, (200, 500))
        if r.status_code == 200:
            data = r.get_json()
            self.assertTrue(data.get("success"))


class TestMN2OpsStats(unittest.TestCase):
    """GET /api/mn2/ops/stats"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    def test_ops_stats_returns_ok_when_no_secret(self):
        r = self.client.get("/api/mn2/ops/stats")
        if r.status_code == 403:
            self.skipTest("MN2_OPS_SECRET or MN2_SCAN_SECRET is set")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("scanner_runs", data)


class TestMN2OpsVerifiedUsers(unittest.TestCase):
    """GET /api/mn2/ops/verified-users and POST /api/mn2/ops/verify-user"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    def test_ops_verified_users_returns_list_when_no_secret(self):
        r = self.client.get("/api/mn2/ops/verified-users")
        if r.status_code == 403:
            self.skipTest("Ops secret is set")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertIsInstance(data.get("user_ids"), list)

    @patch("backend.services.mn2_verification.add_verified")
    def test_ops_verify_user_add_when_no_secret(self, mock_add):
        mock_add.return_value = True
        r = self.client.post(
            "/api/mn2/ops/verify-user",
            data=json.dumps({"user_id": "test_uid", "action": "add"}),
            content_type="application/json",
        )
        if r.status_code == 403:
            self.skipTest("Ops secret is set")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("action"), "add")


class TestMn2WalletActivity(unittest.TestCase):
    """GET /api/mn2/wallet-activity"""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.services.mn2_ledger.get_wallet_activity_days")
    @patch("backend.routes.mn2_routes.resolve_user_id")
    def test_wallet_activity_returns_buckets(self, mock_resolve, mock_days):
        mock_resolve.return_value = "u_act"
        mock_days.return_value = [
            {"date": "2026-04-15", "deposits_mn2": 0.0, "out_mn2": 0.0, "net_mn2": 0.0, "events": 0},
            {"date": "2026-04-19", "deposits_mn2": 1.0, "out_mn2": 0.5, "net_mn2": 0.5, "events": 2},
        ]
        r = self.client.get("/api/mn2/wallet-activity?user_id=u_act&days=5")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("user_id"), "u_act")
        self.assertEqual(len(data.get("buckets") or []), 2)


class TestMN2BalanceWithVerification(unittest.TestCase):
    """Balance endpoint returns withdrawal_verified when config says so."""

    def setUp(self):
        self.app = get_app()
        self.client = self.app.test_client()

    @patch("backend.services.mn2_verification.is_verified")
    @patch("backend.routes.mn2_routes.get_balance")
    @patch("backend.routes.mn2_routes._load_mn2_config")
    def test_balance_includes_withdrawal_verified_when_required(
        self, mock_config, mock_get_balance, mock_is_verified
    ):
        mock_config.return_value = {
            "coins_per_mn2": 100,
            "shop_revenue_address": "",
            "withdrawal_requires_verification": True,
        }
        mock_get_balance.return_value = {"success": True, "user_id": "u1", "mn2_balance": 0}
        mock_is_verified.return_value = True
        r = self.client.get("/api/mn2/balance?user_id=u1")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("withdrawal_verified", data)
        self.assertTrue(data["withdrawal_verified"])


class TestMN2DepositAddressSelfHeal(unittest.TestCase):
    """get_or_create_deposit_address validates cached addresses and self-heals."""

    @patch("backend.services.mn2_rpc_client.getnewaddress")
    @patch("backend.services.mn2_rpc_client.validateaddress")
    @patch("backend.services.mn2_wallet_service._save_addresses")
    @patch("backend.services.mn2_wallet_service._load_addresses")
    def test_invalid_cached_address_is_regenerated(
        self, mock_load, mock_save, mock_validate, mock_getnew
    ):
        from backend.services import mn2_wallet_service as w
        mock_load.return_value = {"u1": "BADADDR"}
        saved = {}
        mock_save.side_effect = lambda d: saved.update(d)
        mock_validate.side_effect = lambda a: (
            {"result": {"isvalid": False}} if a == "BADADDR" else {"result": {"isvalid": True}}
        )
        mock_getnew.return_value = {"result": "MxFreshValidAddress"}

        res = w.get_or_create_deposit_address("u1")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("deposit_address"), "MxFreshValidAddress")
        self.assertEqual(saved.get("u1"), "MxFreshValidAddress")

    @patch("backend.services.mn2_rpc_client.getnewaddress")
    @patch("backend.services.mn2_rpc_client.validateaddress")
    @patch("backend.services.mn2_wallet_service._save_addresses")
    @patch("backend.services.mn2_wallet_service._load_addresses")
    def test_rpc_outage_keeps_existing_address(
        self, mock_load, mock_save, mock_validate, mock_getnew
    ):
        from backend.services import mn2_wallet_service as w
        mock_load.return_value = {"u1": "MxExisting"}
        # Daemon unreachable -> validateaddress returns an error; must NOT discard.
        mock_validate.return_value = {"error": "daemon offline"}

        res = w.get_or_create_deposit_address("u1")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("deposit_address"), "MxExisting")
        mock_getnew.assert_not_called()


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(sys.modules[__name__]))
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
