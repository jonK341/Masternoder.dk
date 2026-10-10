#!/usr/bin/env python3
"""Tests for bringing rented/paid masternodes online without explorer hangs."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


class TestRentedMasternodesSnapshot(unittest.TestCase):
    def test_snapshot_empty_registry_daemon_down(self):
        from backend.services import mn2_masternode_service as mn

        with patch.object(mn, "list_hosts", return_value=[]):
            with patch(
                "backend.services.mn2_daemon_health_service.probe_daemon",
                return_value={"healthy": False, "health": {"status": "unreachable"}},
            ):
                with patch(
                    "backend.services.mn2_masternode_hosting_service.paid_rental_stats",
                    return_value={"paid_orders": 0, "paid_slots": 0, "missing_host_rows": 0},
                ):
                    snap = mn.rented_masternodes_snapshot()
        self.assertTrue(snap.get("success"))
        self.assertFalse(snap.get("can_bring_online"))
        self.assertIn("masternoder2d_rpc_unreachable", snap.get("blockers") or [])
        self.assertIn("no_rented_hosts_in_registry", snap.get("blockers") or [])

    def test_snapshot_can_bring_online_when_pending_and_healthy(self):
        from backend.services import mn2_masternode_service as mn

        hosts = [{
            "id": "user-abc-111111",
            "label": "Hosted MN",
            "status": "provisioning",
            "collateral_txid": "abc",
            "owner_user_id": "u1",
        }]
        with patch.object(mn, "list_hosts", return_value=hosts):
            with patch(
                "backend.services.mn2_daemon_health_service.probe_daemon",
                return_value={"healthy": True, "health": {"status": "healthy"}},
            ):
                with patch(
                    "backend.services.mn2_masternode_hosting_service.paid_rental_stats",
                    return_value={"paid_orders": 1, "paid_slots": 1, "missing_host_rows": 0},
                ):
                    snap = mn.rented_masternodes_snapshot()
        self.assertTrue(snap.get("can_bring_online"))
        self.assertEqual(snap.get("host_count"), 1)
        self.assertEqual(len(snap.get("pending") or []), 1)

    def test_bring_online_stops_when_daemon_down(self):
        from backend.services import mn2_masternode_service as mn

        snap = {
            "success": True,
            "daemon_healthy": False,
            "auto_provision": True,
            "host_count": 1,
            "paid_orders": 1,
            "blockers": ["masternoder2d_rpc_unreachable"],
        }
        with patch(
            "backend.services.mn2_masternode_hosting_service.ensure_paid_hosts_in_registry",
            return_value={"success": True, "created": [], "restored": []},
        ):
            with patch.object(mn, "rented_masternodes_snapshot", return_value=snap):
                out = mn.bring_rented_masternodes_online()
        self.assertFalse(out.get("success"))
        self.assertIn("daemon RPC is down", out.get("error") or "")
        self.assertIsNone(out.get("provision"))

    def test_bring_online_provisions_and_starts_when_healthy(self):
        from backend.services import mn2_masternode_service as mn

        snap = {
            "success": True,
            "daemon_healthy": True,
            "auto_provision": True,
            "host_count": 1,
            "paid_orders": 1,
            "pending": [{"id": "user-abc-111111"}],
        }
        with patch(
            "backend.services.mn2_masternode_hosting_service.ensure_paid_hosts_in_registry",
            return_value={"success": True, "created_count": 0, "restored_count": 1, "created": [], "restored": ["user-abc-111111"]},
        ):
            with patch.object(mn, "rented_masternodes_snapshot", return_value=snap):
                with patch.object(mn, "process_pending_hosts", return_value={"success": True, "processed": 1}) as prov:
                    with patch.object(mn, "start_rented_hosts_via_rpc", return_value={"success": True, "started_ok": 1}) as start:
                        with patch.object(mn, "maintain_ping_loop", return_value={"success": True}):
                            out = mn.bring_rented_masternodes_online(limit=5)
        self.assertTrue(out.get("success"))
        prov.assert_called_once_with(limit=5, skip_explorer=True)
        start.assert_called_once_with(limit=5)
        self.assertEqual(out.get("starts", {}).get("started_ok"), 1)


class TestPaidOrderRegistryRestore(unittest.TestCase):
    def test_ensure_paid_hosts_restores_missing_ids(self):
        from backend.services import mn2_masternode_hosting_service as hosting
        from backend.services import mn2_masternode_service as mn

        with tempfile.TemporaryDirectory() as tmp:
            orders_path = os.path.join(tmp, "mn2_masternode_orders.json")
            hosts_path = os.path.join(tmp, "mn2_masternode_hosts.json")
            with open(orders_path, "w", encoding="utf-8") as f:
                json.dump({
                    "mnq_test1": {
                        "order_id": "mnq_test1",
                        "status": "paid",
                        "user_id": "alice",
                        "slots": 1,
                        "host_ids": ["user-alice-aaaaaa"],
                    }
                }, f)
            with open(hosts_path, "w", encoding="utf-8") as f:
                json.dump({"hosts": []}, f)

            def _host_data(name):
                if name == "mn2_masternode_hosts.json":
                    return hosts_path
                if name == "mn2_masternode_config.json":
                    return os.path.join(BASE, "data", "mn2_masternode_config.json")
                return os.path.join(tmp, name)

            with patch.object(hosting, "_data_path", return_value=orders_path):
                with patch.object(mn, "_data_path", side_effect=_host_data):
                    out = hosting.ensure_paid_hosts_in_registry()
                    hosts = mn.list_hosts(include_internal=True)
            self.assertTrue(out.get("success"))
            self.assertEqual(out.get("restored_count"), 1)
            self.assertEqual(hosts[0].get("id"), "user-alice-aaaaaa")
            self.assertEqual(hosts[0].get("status"), "provisioning")

    def test_paid_rental_stats_counts_missing_rows(self):
        from backend.services import mn2_masternode_hosting_service as hosting

        orders = {
            "a": {"status": "paid", "slots": 2, "host_ids": []},
            "b": {"status": "quoted", "slots": 9},
        }
        with patch.object(hosting, "_load_orders", return_value=orders):
            stats = hosting.paid_rental_stats(existing_host_ids=set())
        self.assertEqual(stats["paid_orders"], 1)
        self.assertEqual(stats["paid_slots"], 2)
        self.assertEqual(stats["missing_host_rows"], 2)


if __name__ == "__main__":
    unittest.main()
