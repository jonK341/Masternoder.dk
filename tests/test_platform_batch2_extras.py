#!/usr/bin/env python3
"""Tests for platform batch-2 extras and profit daemon session upgrades."""
from __future__ import annotations

import io
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
        with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
            from src.app import create_app
            _app = create_app()
    return _app


class TestPlatformBatch2Extras(unittest.TestCase):
    def setUp(self):
        self.client = get_app().test_client()

    def test_combined_after_session(self):
        r = self.client.get("/api/platform/upgrades/combined")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data["batch2"]["done"], 200)
        self.assertEqual(data["batch2"]["planned"], 0)
        self.assertEqual(data["batch2"]["done"] + data["batch2"]["planned"], 200)

    def test_explorer_remaining_extras(self):
        r = self.client.get("/api/platform/batch2/explorer/widgets")
        self.assertEqual(r.status_code, 200)
        rem = ((r.get_json() or {}).get("batch2_extras") or {}).get("remaining") or {}
        self.assertIn("market_activity_deltas", rem)
        self.assertIn("fee_suggestion_strip", rem)

    def test_generator_reorder_queue(self):
        r = self.client.post(
            "/api/platform/generator/reorder-queue",
            json={"job_ids": ["j1", "j2"]},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json().get("success"))

    def test_wallet_qr(self):
        r = self.client.get("/api/platform/batch2/explorer/wallet-qr?address=MN2TEST")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("qr_url", data)

    def test_exchange_widgets_has_extras(self):
        r = self.client.get("/api/platform/batch2/exchange/widgets")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data.get("success"))
        ex = data.get("batch2_extras") or {}
        self.assertIn("liquidity_heatmap", ex)
        self.assertIn("treasury_sparkline", ex)

    def test_generator_widgets_has_extras(self):
        r = self.client.get("/api/platform/batch2/generator/widgets?user_id=test_user")
        self.assertEqual(r.status_code, 200)
        ex = (r.get_json() or {}).get("batch2_extras") or {}
        self.assertIn("cost_estimator", ex)

    def test_batch2_extras_route(self):
        r = self.client.get("/api/platform/batch2/quest/extras?user_id=u1")
        self.assertEqual(r.status_code, 200)
        ex = (r.get_json() or {}).get("batch2_extras") or {}
        self.assertIn("ai_quest_cta", ex)

    def test_quest_claim_all(self):
        with patch(
            "backend.services.trophy_quest_service.get_unified_quests",
            return_value={"quests": [{"id": "q1", "claimable": True}]},
        ), patch(
            "backend.services.trophy_quest_service.claim_quest",
            return_value={"success": True},
        ):
            r = self.client.get("/api/platform/quests/claim-all?user_id=u1")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json().get("success"))


class TestProfitDaemonSessionUpgrades(unittest.TestCase):
    def setUp(self):
        self.client = get_app().test_client()

    def test_slippage_guard_blocks_shallow_book(self):
        from backend.services.profit_daemon_ops_service import check_slippage_guard
        out = check_slippage_guard(
            {"symbol": "DOGE", "buy_venue": "binance", "buy_ask": 0.1, "buy_depth_usd": 10},
            notional_usd=25,
        )
        self.assertFalse(out.get("ok"))

    def test_triangular_gate(self):
        from backend.services.profit_daemon_ops_service import triangular_live_allowed
        gate = triangular_live_allowed()
        self.assertIn("paper_only", gate)

    def test_ppp_timeseries_export(self):
        from backend.services.profit_daemon_ops_service import ppp_timeseries_export
        data = ppp_timeseries_export(hours=24)
        self.assertTrue(data.get("success"))
        self.assertIn("points", data)

    def test_volatility_windows_service(self):
        from backend.services.exchange_profit_pair_search_service import volatility_window_scores
        windows = volatility_window_scores("DOGE")
        self.assertIsInstance(windows, dict)

    def test_metrics_near_threshold_key(self):
        from backend.services.profit_daemon_ops_service import daemon_metrics_snapshot
        snap = daemon_metrics_snapshot()
        self.assertIn("near_threshold", snap)

    def test_meme_coin_filter(self):
        from backend.services.exchange_profit_pair_search_service import _apply_meme_coin_filter, search_config
        with patch(
            "backend.services.exchange_profit_pair_search_service.search_config",
            return_value={**search_config(), "exclude_meme_coins": True, "meme_coin_symbols": ["DOGE"]},
        ):
            out = _apply_meme_coin_filter(["BTC", "DOGE", "ETH"])
        self.assertNotIn("DOGE", out)

    def test_force_attempt_budget(self):
        from backend.services.profit_daemon_ops_service import force_attempt_budget_state, record_force_attempt
        st = force_attempt_budget_state()
        self.assertTrue(st.get("success"))
        self.assertIn("cap", st)
        record_force_attempt()

    def test_venue_min_notional_floors(self):
        from backend.services.profit_daemon_ops_service import venue_min_notional_floors
        floors = venue_min_notional_floors()
        self.assertTrue(floors.get("success"))
        self.assertIn("binance", floors.get("floors_usd", {}))

    def test_tax_export_csv(self):
        from backend.services.profit_daemon_ops_service import tax_export_csv
        data = tax_export_csv(season="2026")
        self.assertTrue(data.get("success"))
        self.assertIn("csv", data)

    def test_casino_skip_on_kill(self):
        from backend.services.profit_daemon_ops_service import casino_agent_tick_skip_on_kill
        out = casino_agent_tick_skip_on_kill()
        self.assertIn("skip_casino_agent_tick", out)

    def test_paper_live_banner(self):
        r = self.client.get("/api/profit-daemon/paper-live-banner")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json().get("success"))

    def test_spork_audit(self):
        r = self.client.get("/api/profit-daemon/spork-audit")
        self.assertEqual(r.status_code, 200)
        self.assertIn("banner_line", r.get_json())


if __name__ == "__main__":
    unittest.main()
