#!/usr/bin/env python3
"""Unit tests for mn2_network_peers_service — no live daemon."""
import os
import re
import sys
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import backend.services.mn2_network_peers_service as peers


class TestPeerParsing(unittest.TestCase):
    def test_parse_host_port(self):
        host, port, err = peers.parse_peer_entry("192.46.237.230:17646", 17646)
        self.assertIsNone(err)
        self.assertEqual(host, "192.46.237.230")
        self.assertEqual(port, 17646)

    def test_parse_default_port(self):
        host, port, err = peers.parse_peer_entry("explorer.masternoder.dk", 17646)
        self.assertIsNone(err)
        self.assertEqual(port, 17646)

    def test_reject_underscore_separator(self):
        _, _, err = peers.parse_peer_entry("144.91.75.27_17646", 17646)
        self.assertIsNotNone(err)
        self.assertIn("invalid separator", err)

    def test_normalize_dedupes(self):
        valid, errors = peers.normalize_addnodes(
            ["85.10.148.5:17646", "85.10.148.5:17646", "bad_17646"],
            17646,
        )
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(errors), 1)


class TestPeerCatalog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        json_data = {
            "version": 99,
            "updated": "2099-01-01",
            "networks": {
                "mainnet": {
                    "p2p_port": 17646,
                    "rpc_port": 9332,
                    "dns_seeds": ["seed.example"],
                    "addnodes": ["1.2.3.4:17646"],
                },
                "testnet": {
                    "p2p_port": 27646,
                    "rpc_port": 19332,
                    "addnodes": ["test.example:27646"],
                },
            },
        }
        import json
        json.dump(json_data, self.tmp)
        self.tmp.close()
        self._orig = peers._PEERS_PATH
        peers._PEERS_PATH = self.tmp.name

    def tearDown(self):
        peers._PEERS_PATH = self._orig
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_get_network_config_mainnet(self):
        cfg = peers.get_network_config("mainnet")
        self.assertEqual(cfg["p2p_port"], 17646)
        self.assertEqual(cfg["rpc_port"], 9332)
        self.assertIn("1.2.3.4:17646", cfg["addnodes"])

    def test_conf_snippet_has_addnode_not_connect(self):
        snip = peers.conf_snippet("mainnet", include_comments=True)
        self.assertIn("addnode=1.2.3.4:17646", snip)
        for line in snip.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                self.assertFalse(stripped.startswith("connect="), stripped)

    def test_peer_health_thresholds(self):
        h0 = peers.peer_health_from_overview({"daemon": {"connections": 0}})
        self.assertEqual(h0["status"], "critical")
        h8 = peers.peer_health_from_overview({"daemon": {"connections": 8}})
        self.assertEqual(h8["status"], "healthy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
