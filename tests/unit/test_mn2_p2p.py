#!/usr/bin/env python3
"""
Unit tests for backend/services/mn2_p2p_service.py (P2P MN2 market, Model B).

Mocks PayPal, points, KYC; temp data dir. No network/app needed.
Run: pytest tests/unit/test_mn2_p2p.py -v
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import backend.services.mn2_p2p_service as p2p


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


class P2PBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig_dir = p2p._data_dir
        p2p._data_dir = lambda: self.tmp
        self.fake = FakePoints()
        self._orig_points = p2p._points
        p2p._points = lambda: self.fake
        self._orig_ledger = p2p._ledger
        p2p._ledger = lambda *a, **k: None
        self._verified = patch.object(p2p, "_is_verified", return_value=True)
        self._verified.start()
        self._held = patch.object(p2p, "_onramp_held", return_value=0.0)
        self._held.start()
        self._cfg = patch.object(p2p, "get_config", return_value={
            "enabled": True, "model": "B", "platform_fee_percent": 10.0, "buyer_spread_percent": 0.0,
            "min_listing_mn2": 1.0, "max_listing_mn2": 5000.0, "max_open_listings_per_seller": 5,
            "requires_seller_verification": True, "seller_must_sell_cleared_only": True,
            "hold_hours": 72, "order_ttl_seconds": 900,
            "daily_usd_cap": 10000.0, "daily_usd_cap_verified": 100000.0, "lifetime_usd_cap_unverified": 500.0,
        })
        self._cfg.start()

    def tearDown(self):
        p2p._data_dir = self._orig_dir
        p2p._points = self._orig_points
        p2p._ledger = self._orig_ledger
        self._verified.stop(); self._held.stop(); self._cfg.stop()

    def _credit(self, uid, amt):
        self.fake.add_points(uid, "mn2_balance", amt)

    def _list(self, seller="seller", mn2=100, price=2.0):
        self._credit(seller, mn2)
        return p2p.create_listing(seller, mn2, price)

    def _buy(self, listing_id, buyer="buyer", mn2=10, pp_order="PP-1"):
        with patch("backend.services.paypal_service.create_order",
                   return_value={"success": True, "order_id": pp_order, "approve_url": "https://x"}):
            return p2p.create_purchase(buyer, listing_id, mn2_amount=mn2)

    def _capture(self, order_id, buyer="buyer", capture_id="CAP-1"):
        with patch("backend.services.paypal_service.capture_order",
                   return_value={"success": True, "status": "COMPLETED", "capture_id": capture_id, "amount": "20.00"}):
            return p2p.capture(order_id, buyer)


class TestListing(P2PBase):
    def test_create_listing_escrows(self):
        r = self._list(mn2=100)
        self.assertTrue(r["success"], r)
        # seller's balance dropped by escrow
        self.assertAlmostEqual(self.fake.store["seller"]["mn2_balance"], 0.0, places=6)

    def test_cannot_list_more_than_cleared(self):
        self._credit("seller", 5)
        r = p2p.create_listing("seller", 10, 2.0)
        self.assertFalse(r["success"])

    def test_seller_must_sell_cleared_only(self):
        self._credit("seller", 100)
        with patch.object(p2p, "_onramp_held", return_value=95.0):
            r = p2p.create_listing("seller", 10, 2.0)
            self.assertFalse(r["success"])

    def test_cancel_refunds_available(self):
        r = self._list(mn2=100)
        c = p2p.cancel_listing("seller", r["listing_id"])
        self.assertTrue(c["success"])
        self.assertAlmostEqual(self.fake.store["seller"]["mn2_balance"], 100.0, places=6)

    def test_disabled_blocks_listing(self):
        with patch.object(p2p, "get_config", return_value={**p2p.get_config(), "enabled": False}):
            self._credit("seller", 100)
            r = p2p.create_listing("seller", 10, 2.0)
            self.assertFalse(r["success"])


class TestBuyFlow(P2PBase):
    def test_buy_reserves_then_capture_credits_buyer_and_holds(self):
        lst = self._list(mn2=100, price=2.0)
        o = self._buy(lst["listing_id"], mn2=10)
        self.assertTrue(o["success"], o)
        self.assertAlmostEqual(o["usd_amount"], 20.0, places=2)  # 10 * $2, 0 spread
        # reserved -> available reduced
        self.assertAlmostEqual(p2p.list_listings()["listings"][0]["mn2_available"], 90.0, places=6)
        cap = self._capture(o["order_id"])
        self.assertTrue(cap["success"], cap)
        self.assertEqual(cap["status"], "held")
        self.assertAlmostEqual(self.fake.store["buyer"]["mn2_balance"], 10.0, places=6)
        # buyer hold blocks withdrawal
        self.assertAlmostEqual(p2p.buyer_held("buyer"), 10.0, places=6)
        # seller payout pending (10% fee on $20 -> seller gets $18)
        ov = p2p.get_user_overview("seller")
        self.assertAlmostEqual(ov["seller_payout_pending_usd"], 18.0, places=2)
        self.assertEqual(ov["seller_payout_usd"], 0.0)

    def test_cannot_overbuy_listing(self):
        lst = self._list(mn2=5, price=2.0)
        o = self._buy(lst["listing_id"], mn2=10)
        self.assertFalse(o["success"])

    def test_cannot_buy_own_listing(self):
        lst = self._list(seller="s1", mn2=100)
        o = self._buy(lst["listing_id"], buyer="s1", mn2=10)
        self.assertFalse(o["success"])

    def test_capture_idempotent(self):
        lst = self._list(mn2=100)
        o = self._buy(lst["listing_id"], mn2=10)
        self._capture(o["order_id"])
        again = self._capture(o["order_id"])
        self.assertTrue(again.get("already"))
        self.assertAlmostEqual(self.fake.store["buyer"]["mn2_balance"], 10.0, places=6)


class TestClearAndDispute(P2PBase):
    def _funded(self):
        lst = self._list(mn2=100, price=2.0)
        o = self._buy(lst["listing_id"], mn2=10)
        self._capture(o["order_id"])
        return o["order_id"]

    def test_clear_matured_releases_payout_and_unlocks_buyer(self):
        oid = self._funded()
        orders = p2p._read(p2p._ORDERS_FILE)
        orders[oid]["payout_release_at"] = "2000-01-01T00:00:00Z"
        orders[oid]["buyer_hold_until"] = "2000-01-01T00:00:00Z"
        p2p._write(p2p._ORDERS_FILE, orders)
        res = p2p.clear_matured()
        self.assertEqual(res["cleared"], 1)
        self.assertAlmostEqual(res["released_seller_usd"], 18.0, places=2)
        self.assertEqual(p2p.buyer_held("buyer"), 0.0)
        ov = p2p.get_user_overview("seller")
        self.assertAlmostEqual(ov["seller_payout_usd"], 18.0, places=2)
        self.assertAlmostEqual(ov["seller_payout_pending_usd"], 0.0, places=2)

    def test_expired_pending_order_restores_listing(self):
        lst = self._list(mn2=100)
        o = self._buy(lst["listing_id"], mn2=10)  # pending, not captured
        orders = p2p._read(p2p._ORDERS_FILE)
        orders[o["order_id"]]["expires_at"] = "2000-01-01T00:00:00Z"
        p2p._write(p2p._ORDERS_FILE, orders)
        res = p2p.clear_matured()
        self.assertEqual(res["expired"], 1)
        self.assertAlmostEqual(p2p.list_listings()["listings"][0]["mn2_available"], 100.0, places=6)

    def test_dispute_claws_back_buyer_and_returns_escrow(self):
        oid = self._funded()
        self.assertAlmostEqual(self.fake.store["buyer"]["mn2_balance"], 10.0, places=6)
        event = {"event_type": "CUSTOMER.DISPUTE.CREATED", "resource": {"custom_id": oid}}
        res = p2p.handle_webhook(event, signature_ok=True)
        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["clawback"]["clawed_back_mn2"], 10.0, places=6)
        # buyer lost the MN2, seller got their escrow back
        self.assertAlmostEqual(self.fake.store["buyer"]["mn2_balance"], 0.0, places=6)
        self.assertAlmostEqual(self.fake.store["seller"]["mn2_balance"], 10.0, places=6)
        ov = p2p.get_user_overview("seller")
        self.assertAlmostEqual(ov["seller_payout_pending_usd"], 0.0, places=2)

    def test_webhook_requires_signature(self):
        res = p2p.handle_webhook({"event_type": "PAYMENT.CAPTURE.COMPLETED"}, signature_ok=False)
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
