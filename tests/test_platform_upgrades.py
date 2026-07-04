#!/usr/bin/env python3
"""Tests for platform 100-upgrade roadmap API."""
import os
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)

_app = None


def get_app():
    global _app
    if _app is None:
        import io
        from unittest.mock import patch
        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            from src.app import create_app
            _app = create_app()
    return _app


class TestPlatformUpgradesRoadmap(unittest.TestCase):
    def setUp(self):
        self.client = get_app().test_client()

    def test_roadmap_returns_100_items(self):
        r = self.client.get("/api/platform/upgrades")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total"), 100)
        self.assertEqual(data.get("done") + data.get("planned"), 100)
        self.assertGreaterEqual(data.get("done"), 25)

    def test_roadmap_area_filter(self):
        r = self.client.get("/api/platform/upgrades?area=explorer")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(len(data.get("items") or []), 10)
        self.assertTrue(all(i.get("area") == "explorer" for i in data["items"]))

    def test_area_summary_explorer(self):
        r = self.client.get("/api/platform/area/explorer/summary")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("area"), "explorer")
        self.assertIn("upgrades_done", data)

    def test_area_summary_unknown(self):
        r = self.client.get("/api/platform/area/invalid/summary")
        self.assertEqual(r.status_code, 404)
        data = r.get_json()
        self.assertFalse(data.get("success"))

    def test_platform_health(self):
        r = self.client.get("/api/platform/health")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("roadmap", data)
        self.assertIn("areas", data)


class TestPlatformUpgradesService(unittest.TestCase):
    def test_catalog_loads(self):
        from backend.services.platform_upgrades_service import get_roadmap
        data = get_roadmap()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], 100)

    def test_all_areas_valid(self):
        from backend.services.platform_upgrades_service import get_area_summary
        for area in (
            "explorer", "exchange", "profile", "shop", "casino",
            "generator", "command-center", "game", "quest", "battle",
        ):
            data = get_area_summary(area, user_id="test_user")
            self.assertTrue(data.get("success"), area)
            self.assertEqual(data.get("area"), area)


if __name__ == "__main__":
    unittest.main()
