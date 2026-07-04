#!/usr/bin/env python3
"""Tests for platform batch-2 upgrades (items 101–300)."""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)

_app = None


def get_app():
    global _app
    if _app is None:
        import io
        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            from src.app import create_app
            _app = create_app()
    return _app


class TestPlatformBatch2Roadmap(unittest.TestCase):
    def setUp(self):
        self.client = get_app().test_client()

    def test_batch2_returns_200_items(self):
        r = self.client.get("/api/platform/upgrades/batch2")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total"), 200)
        self.assertEqual(data.get("done") + data.get("planned"), 200)
        self.assertGreaterEqual(data.get("done"), 40)

    def test_batch2_area_filter(self):
        r = self.client.get("/api/platform/upgrades/batch2?area=casino")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(len(data.get("items") or []), 20)
        self.assertTrue(all(i.get("area") == "casino" for i in data["items"]))

    def test_combined_totals(self):
        r = self.client.get("/api/platform/upgrades/combined")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("combined_total"), 300)
        self.assertGreaterEqual(data.get("combined_done"), 60)

    def test_batch2_widgets_casino(self):
        r = self.client.get("/api/platform/batch2/casino/widgets?user_id=test_user")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("area"), "casino")
        self.assertIn("batch2_done", data)

    def test_batch2_widgets_unknown(self):
        r = self.client.get("/api/platform/batch2/invalid/widgets")
        self.assertEqual(r.status_code, 404)


class TestBatch2Routes(unittest.TestCase):
    def setUp(self):
        self.client = get_app().test_client()

    def test_shop_daily_deal_ui(self):
        with patch("backend.routes.shop_routes._get_shop_items", return_value=[
            {"id": "x", "name": "Test Pack", "category": "themes", "price": 200},
        ]):
            r = self.client.get("/api/shop/daily-deal/ui")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("headline", data)
        self.assertIn("discount_pct", data)

    def test_casino_wins_ticker(self):
        with patch(
            "backend.services.casino_agents_service.get_spectator_feed",
            return_value={"success": True, "events": [
                {"net": 50, "agent_name": "Bot1", "game": "dice", "ts": "2026-07-04T12:00:00Z"},
            ]},
        ), patch(
            "backend.services.casino_agents_service.tick_summary",
            return_value={"success": True, "win_rate_pct": 55.0, "total_ticks": 10},
        ):
            r = self.client.get("/api/casino/wins/ticker?limit=5")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(len(data.get("wins") or []), 1)

    def test_battle_matchmaking_status(self):
        with patch(
            "backend.routes.battle_routes._get_battle_stats",
            return_value={"total_battles": 10, "wins": 6, "win_streak": 2},
        ):
            r = self.client.get("/api/battle/matchmaking/status?user_id=u1")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("recommended_difficulty"), "hard")


class TestBatch2Service(unittest.TestCase):
    def test_catalog_loads(self):
        from backend.services.platform_upgrades_batch2_service import get_batch2_roadmap
        data = get_batch2_roadmap()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], 200)

    def test_all_areas_widgets(self):
        from backend.services.platform_upgrades_batch2_service import get_batch2_widgets
        for area in (
            "explorer", "exchange", "profile", "shop", "casino",
            "generator", "command-center", "game", "quest", "battle",
        ):
            data = get_batch2_widgets(area, user_id="test_user")
            self.assertTrue(data.get("success"), area)
            self.assertEqual(data.get("area"), area)


if __name__ == "__main__":
    unittest.main()
