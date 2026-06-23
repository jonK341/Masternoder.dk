#!/usr/bin/env python3
"""
Unit tests for backend/services/mn2_onramp_service.py (PayPal -> MN2 Model A).

Mocks PayPal, MN2 price, points and KYC; uses a temp data dir. No network/app needed.
Run: pytest tests/unit/test_mn2_onramp.py -v
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import backend.services.mn2_onramp_service as onramp


class FakePoints:
    def __init__(self):
        self.store = {}

    def add_points(self, uid, pt, amt, source=None, metadata=None):
        self.store.setdefault(uid, {}).setdefault(pt, 0.0)
        self.store[uid][pt] += float(amt)
        return {"success": True}

    def get_all_points(self, uid):
        s = self.store.get(uid, {})
        return {"success": True, "points": {"mn2_balance": float(s.get("mn2_balance", 0.0))}}


class OnrampBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_dir = onramp._data_dir
        onramp._data_dir = lambda: self.tmp
        self.fake = FakePoints()
        self._orig_points = onramp._points
        onramp._points = lambda: self.fake
        self._orig_ledger = onramp._ledger
        onramp._ledger = lambda *a, **k: None
        self._price = patch.object(onramp, "_mn2_usd_price", return_value=5.0)
        self._price.start()
        self._verified = patch.object(onramp, "_is_verified", return_value=False)
        self._verified.start()
        # fixed config (avoid reading staking config file)
        self._cfg = patch.object(onramp, "get_config", return_value={
            "enabled": True, "model": "A", "spread_percent": 0.0, "quote_ttl_seconds": 60,
            "hold_hours": 72, "daily_usd_cap": 200.0, "daily_usd_cap_verified": 2000.0,
            "lifetime_usd_cap_unverified": 50.0, "min_usd": 1.0, "max_usd_per_order": 1000.0,
        })
        self._cfg.start()

    def tearDown(self):
        onramp._data_dir = self._orig_dir
        onramp._points = self._orig_points
        onramp._ledger = self._orig_ledger
        self._price.stop(); self._verified.stop(); self._cfg.stop()

    def _quote(self, usd=10, uid="u1"):
        return onramp.get_quote(usd, uid)

    def _order(self, quote_id, uid="u1", pp_order_id="PP-ORDER-1"):
        with patch("backend.services.paypal_service.create_order",
                   return_value={"success": True, "order_id": pp_order_id, "approve_url": "https://x"}):
            return onramp.create_order(quote_id, uid)

    def _capture(self, order_id, uid="u1", capture_id="CAP-1"):
        with patch("backend.services.paypal_service.capture_order",
                   return_value={"success": True, "status": "COMPLETED", "capture_id": capture_id, "amount": "10.00"}):
            return onramp.capture(order_id, uid)


class TestQuote(OnrampBase):
    def test_quote_math(self):
        q = self._quote(10)
        self.assertTrue(q["success"])
        # price 5 USD/MN2, 0 spread -> 2 MN2 for $10
        self.assertAlmostEqual(q["mn2_amount"], 2.0, places=6)

    def test_quote_below_min(self):
        self.assertFalse(self._quote(0.5)["success"])

    def test_quote_price_unavailable(self):
        with patch.object(onramp, "_mn2_usd_price", return_value=None):
            self.assertFalse(self._quote(10)["success"])

    def test_lifetime_cap_unverified(self):
        # cap is $50; first $40 funded, next $20 quote should be blocked
        q1 = self._quote(40); o1 = self._order(q1["quote_id"]); self._capture(o1["order_id"])
        q2 = self._quote(20)
        self.assertFalse(q2["success"])
        self.assertEqual(q2.get("code"), "cap_exceeded")


class TestOrderCaptureHold(OnrampBase):
    def test_full_flow_credits_and_holds(self):
        q = self._quote(10)
        o = self._order(q["quote_id"])
        self.assertTrue(o["success"])
        self.assertEqual(o["paypal_order_id"], "PP-ORDER-1")
        cap = self._capture(o["order_id"])
        self.assertTrue(cap["success"])
        self.assertEqual(cap["status"], "held")
        self.assertAlmostEqual(self.fake.store["u1"]["mn2_balance"], 2.0, places=6)
        # held until clearance -> not withdrawable yet
        self.assertAlmostEqual(onramp.held_amount("u1"), 2.0, places=6)

    def test_capture_idempotent(self):
        q = self._quote(10); o = self._order(q["quote_id"])
        self._capture(o["order_id"])
        again = self._capture(o["order_id"])
        self.assertTrue(again.get("already"))
        self.assertAlmostEqual(self.fake.store["u1"]["mn2_balance"], 2.0, places=6)

    def test_clear_matured_makes_withdrawable(self):
        q = self._quote(10); o = self._order(q["quote_id"]); self._capture(o["order_id"])
        # force hold_until into the past
        orders = onramp._load_orders()
        orders[o["order_id"]]["hold_until"] = "2000-01-01T00:00:00Z"
        onramp._save_orders(orders)
        res = onramp.clear_matured()
        self.assertEqual(res["cleared"], 1)
        self.assertEqual(onramp.held_amount("u1"), 0.0)
        st = onramp.get_status(o["order_id"], "u1")
        self.assertTrue(st["withdrawable"])

    def test_cannot_order_expired_quote(self):
        q = self._quote(10)
        orders = onramp._load_orders()
        orders[q["quote_id"]]["expires_at"] = "2000-01-01T00:00:00Z"
        onramp._save_orders(orders)
        o = self._order(q["quote_id"])
        self.assertFalse(o["success"])
        self.assertEqual(o.get("code"), "quote_expired")


class TestWebhookClawback(OnrampBase):
    def _funded_order(self):
        q = self._quote(10); o = self._order(q["quote_id"]); self._capture(o["order_id"])
        return o["order_id"]

    def test_dispute_claws_back(self):
        oid = self._funded_order()
        self.assertAlmostEqual(self.fake.store["u1"]["mn2_balance"], 2.0, places=6)
        event = {"event_type": "CUSTOMER.DISPUTE.CREATED", "resource": {"custom_id": oid}}
        res = onramp.handle_webhook(event, signature_ok=True)
        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["clawback"]["clawed_back_mn2"], 2.0, places=6)
        self.assertAlmostEqual(self.fake.store["u1"]["mn2_balance"], 0.0, places=6)
        st = onramp.get_status(oid, "u1")
        self.assertEqual(st["status"], "charged_back")

    def test_webhook_requires_signature(self):
        res = onramp.handle_webhook({"event_type": "PAYMENT.CAPTURE.COMPLETED"}, signature_ok=False)
        self.assertFalse(res["success"])

    def test_clawback_records_shortfall_when_spent(self):
        oid = self._funded_order()
        # user spent 1.5 MN2 elsewhere; only 0.5 left to claw back
        self.fake.store["u1"]["mn2_balance"] = 0.5
        event = {"event_type": "PAYMENT.CAPTURE.REVERSED", "resource": {"custom_id": oid}}
        res = onramp.handle_webhook(event, signature_ok=True)
        self.assertAlmostEqual(res["clawback"]["clawed_back_mn2"], 0.5, places=6)
        self.assertAlmostEqual(res["clawback"]["shortfall_mn2"], 1.5, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
