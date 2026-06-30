#!/usr/bin/env python3
"""Unit tests for mn2_wallet_hub_service aggregators."""
import os
import sys
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from backend.services import mn2_wallet_hub_service as hub
from backend.services import mn2_release_catalog_service as rel


class TestReleaseCatalogQt(unittest.TestCase):
    def test_qt_downloads_have_sha256_and_fallback_url(self):
        cat = rel.get_release_catalog()
        self.assertTrue(cat.get("success"))
        downloads = {d["id"]: d for d in cat.get("downloads") or []}
        win = downloads.get("qt_windows") or {}
        lin = downloads.get("qt_linux") or {}
        self.assertTrue(win.get("sha256"))
        self.assertTrue(lin.get("sha256"))
        self.assertIn("v1.2.2.0", win.get("url", ""))
        self.assertIn("MasterNoder2-qt-win.zip", win.get("url", ""))


class TestWalletHub(unittest.TestCase):
    def setUp(self):
        hub._CACHE.clear()

    @patch("backend.services.mn2_wallet_service.get_balance")
    @patch("backend.services.mn2_spork_service.gate_status")
    def test_wallet_hub_shape(self, mock_gates, mock_bal):
        mock_bal.return_value = {"success": True, "mn2_balance": 1.5, "user_id": "u1"}
        mock_gates.return_value = {"gates_enabled": True, "maintenance_mode": False}
        out = hub.wallet_hub("u1")
        self.assertTrue(out.get("success"))
        self.assertEqual(out["balance"]["mn2_balance"], 1.5)
        self.assertIn("network", out)
        self.assertIn("spork_gates", out)

    @patch("backend.services.mn2_ledger.get_entries_by_user")
    def test_recent_transactions_merges_custodial(self, mock_entries):
        mock_entries.return_value = [
            {"type": "deposit", "amount": 2.0, "created_at": "2026-06-30T12:00:00Z"},
        ]
        with patch("backend.services.mn2_wallet_service.get_or_create_deposit_address", return_value={"success": False}), \
             patch("backend.services.crypto_exchange_service.list_trades", return_value={"success": True, "trades": []}):
            out = hub.recent_transactions_feed("u1", limit=10)
        self.assertTrue(out.get("success"))
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["transactions"][0]["source"], "custodial")

    @patch("backend.services.mn2_masternode_service.get_service_status")
    @patch("backend.services.exchange_rental_service.rental_catalog")
    def test_rental_overview(self, mock_rental, mock_host):
        mock_host.return_value = {"success": True, "slots_available": 3, "enabled_count": 5}
        mock_rental.return_value = {"success": True, "enabled": True, "rentals": [{"id": "r1", "name": "Starter"}]}
        out = hub.rental_overview()
        self.assertTrue(out.get("success"))
        self.assertEqual(out["masternode_hosting"]["slots_available"], 3)
        self.assertEqual(out["agent_rental"]["listing_count"], 1)

    @patch("backend.services.mn2_explorer_data.recent_blocks", return_value=[])
    @patch("backend.services.mn2_explorer_data.masternodes", return_value={"total": 2, "enabled": 1})
    @patch("backend.services.mn2_spork_service.gate_status", return_value={"maintenance_mode": False})
    def test_public_network_dashboard(self, *_mocks):
        out = hub.public_network_dashboard()
        self.assertTrue(out.get("success"))
        self.assertIn("network", out)
        self.assertIn("spork_gates", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
