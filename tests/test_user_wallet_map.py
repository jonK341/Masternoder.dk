#!/usr/bin/env python3
"""Tests for user wallet map and clone detection."""
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


class TestUserWalletMap(unittest.TestCase):
    def test_detect_clone_groups_by_fingerprint(self):
        from backend.services.user_wallet_map_service import detect_clone_groups

        rows = [
            {"user_id": "user_a", "device_fingerprint": "fingerprint_same_abc", "email": None, "username": "a"},
            {"user_id": "user_b", "device_fingerprint": "fingerprint_same_abc", "email": None, "username": "b"},
            {"user_id": "user_c", "device_fingerprint": "fingerprint_other_xyz", "email": None, "username": "c"},
        ]
        meta = detect_clone_groups(rows)
        self.assertTrue(meta["user_a"]["is_clone_copy"])
        self.assertTrue(meta["user_b"]["is_clone_copy"])
        self.assertEqual(meta["user_a"]["clone_siblings"], 2)
        self.assertNotIn("user_c", meta)

    def test_is_system_user(self):
        from backend.services.user_wallet_map_service import _is_system_user

        self.assertTrue(_is_system_user("pool_1"))
        self.assertTrue(_is_system_user("agent:foo"))
        self.assertFalse(_is_system_user("user_real"))


if __name__ == "__main__":
    unittest.main()
