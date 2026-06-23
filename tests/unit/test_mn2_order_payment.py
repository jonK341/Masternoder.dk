"""
Unit tests for MN2 on-chain order-payment service (V9.2 upgrades).

Covers the new grace-window matching, confirmation tracking, and amount-received
recording. State is isolated by pointing the service at a temp data file; no RPC
or Flask app context is required.
"""
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

import pytest

from backend.services import mn2_order_payment_service as ops


@pytest.fixture
def temp_store(monkeypatch):
    tmp_dir = tempfile.mkdtemp(prefix="mn2_ops_test_")
    store_path = os.path.join(tmp_dir, "mn2_order_payments.json")
    cfg = {
        "order_payment_expiry_hours": 1,
        "order_payment_grace_hours": 24,
        "order_payment_match_tolerance": 0.00000001,
    }
    monkeypatch.setattr(ops, "_path", lambda: store_path)
    monkeypatch.setattr(ops, "_config", lambda: dict(cfg))
    try:
        yield store_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _mk(addr="ADDR1", amount=1.5):
    return ops.create_order_payment(
        user_id="u1", item_id="i1", item_name="Item One", quantity=1,
        price_coins=150, price_mn2=amount, address=addr,
    )


def test_create_sets_progress_fields(temp_store):
    order = _mk()
    assert order["status"] == "pending"
    assert order["confirmations"] == 0
    assert order["amount_received"] is None
    assert order["expires_at"]


def test_address_map_includes_pending(temp_store):
    _mk(addr="ADDRX")
    m = ops.get_address_to_order_map()
    assert "ADDRX" in m


def test_address_map_grace_window(temp_store):
    order = _mk(addr="ADDRG")
    # Force the order to look expired 2h ago — still inside the 24h grace window.
    orders = ops._load()
    orders[0]["expires_at"] = (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
    ops._save(orders)

    assert "ADDRG" in ops.get_address_to_order_map()  # default grace from config (24h)
    assert "ADDRG" not in ops.get_address_to_order_map(grace_hours=0)  # no grace -> dropped


def test_record_order_seen_sets_confirming(temp_store):
    order = _mk(addr="ADDRC")
    ref = order["payment_ref"]
    updated = ops.record_order_seen(ref, "txhash", 3, amount_received=1.5)
    assert updated["status"] == "confirming"
    assert updated["confirmations"] == 3
    assert updated["amount_received"] == 1.5
    # Confirming orders are still scannable.
    assert "ADDRC" in ops.get_address_to_order_map()


def test_mark_underpaid(temp_store):
    order = _mk(addr="ADDRU", amount=2.0)
    ref = order["payment_ref"]
    updated = ops.mark_underpaid(ref, "txhash2", 1.2)
    assert updated["status"] == "underpaid"
    assert updated["amount_received"] == 1.2
    # Underpaid orders drop out of the scan map.
    assert "ADDRU" not in ops.get_address_to_order_map()


def test_confirm_and_fulfill_records_amount(temp_store, monkeypatch):
    order = _mk(addr="ADDRF", amount=1.5)
    ref = order["payment_ref"]

    # Stub the heavy fulfilment dependencies so we exercise only the service's
    # bookkeeping (status + amount_received persistence).
    import backend.services.shop_db_service as dbsvc
    import backend.services.mn2_ledger as ledger
    monkeypatch.setattr(dbsvc, "fulfill_shop_purchase", lambda **k: "purchase-1", raising=False)
    monkeypatch.setattr(ledger, "append_entry", lambda **k: None, raising=False)

    import backend.routes.shop_routes as sr
    monkeypatch.setattr(sr, "_get_shop_items", lambda: [], raising=False)
    monkeypatch.setattr(sr, "_apply_shop_item_effects", lambda *a, **k: None, raising=False)

    result = ops.confirm_and_fulfill(ref, "txfulfill", amount_received=1.75)
    assert result["status"] == "fulfilled"
    assert result["amount_received"] == 1.75
    assert result["txid"] == "txfulfill"


# --------------------------------------------------------------------------
# apply_order_payment policy (scanner helper) — over/under/combined fulfilment
# --------------------------------------------------------------------------

from backend.services import mn2_deposit_scanner as scanner


class _FakePts:
    def __init__(self):
        self.bal = {}
        self.calls = []

    def get_all_points(self, uid):
        return {"points": {"mn2_balance": self.bal.get(uid, 0.0)}}

    def add_points(self, uid, point_type, amount, source=None, metadata=None):
        self.bal[uid] = round(self.bal.get(uid, 0.0) + float(amount), 8)
        self.calls.append((uid, point_type, float(amount), source))
        return {"success": True}


def _apply(amount, confirmations, *, required=1.5, pre_balance=0.0, combined_fulfill=True,
           underpay_credit=True, fulfill_status="fulfilled"):
    order = {"payment_ref": "ref1", "amount_mn2": required, "user_id": "u1", "address": "ADDR"}
    pts = _FakePts()
    pts.bal["u1"] = pre_balance
    appended, seen, under = [], [], []

    def confirm(ref, txid, amount_received=None):
        return {"status": fulfill_status, "payment_ref": ref}

    res = scanner.apply_order_payment(
        order, amount, confirmations, "tx1",
        required_confirmations=6, match_tol=1e-8,
        overpay_credit=True, underpay_credit=underpay_credit, combined_fulfill=combined_fulfill,
        points_db=pts, append_entry=lambda **k: appended.append(k), confirm_and_fulfill=confirm,
        record_order_seen=lambda *a, **k: seen.append((a, k)),
        mark_underpaid=lambda *a, **k: under.append((a, k)),
        get_mn2_balance=lambda uid: pts.bal.get(uid, 0.0),
    )
    return res, pts, appended, seen, under


def test_apply_confirming_records_progress_only():
    res, pts, appended, seen, under = _apply(1.5, confirmations=2)
    assert res["action"] == "confirming"
    assert seen and not appended
    assert pts.bal["u1"] == 0.0  # nothing credited yet


def test_apply_exact_fulfils_without_change():
    res, pts, appended, seen, under = _apply(1.5, confirmations=6)
    assert res["action"] == "fulfilled"
    assert res["overpay"] == 0.0
    assert pts.bal["u1"] == 0.0


def test_apply_overpay_refunds_excess():
    res, pts, appended, seen, under = _apply(2.0, confirmations=6)
    assert res["action"] == "fulfilled"
    assert round(res["overpay"], 8) == 0.5
    assert pts.bal["u1"] == 0.5  # excess credited back
    assert any(a["entry_type"] == "order_overpay_change" for a in appended)


def test_apply_underpay_autocompletes_from_balance():
    # Short 0.5 on a 1.5 order, but user already holds 1.0 -> credit 1.0 then debit 1.5.
    res, pts, appended, seen, under = _apply(1.0, confirmations=6, pre_balance=1.0)
    assert res["action"] == "fulfilled_from_balance"
    assert round(res["debited"], 8) == 1.5
    assert round(pts.bal["u1"], 8) == 0.5  # 1.0 + 1.0 credit - 1.5 debit
    assert not under  # not left underpaid


def test_apply_underpay_credits_when_balance_insufficient():
    res, pts, appended, seen, under = _apply(0.5, confirmations=6, pre_balance=0.0)
    assert res["action"] == "underpaid_credited"
    assert pts.bal["u1"] == 0.5  # received amount kept as credit
    assert under  # marked underpaid


def test_apply_underpay_no_combined_when_disabled():
    res, pts, appended, seen, under = _apply(0.5, confirmations=6, pre_balance=10.0, combined_fulfill=False)
    assert res["action"] == "underpaid_credited"
    assert pts.bal["u1"] == 10.5  # credited, never debited
    assert under


def test_apply_underpay_uncredited_when_policy_off():
    res, pts, appended, seen, under = _apply(0.5, confirmations=6, underpay_credit=False)
    assert res["action"] == "underpaid_uncredited"
    assert pts.bal.get("u1", 0.0) == 0.0


def test_apply_combined_refunds_on_fulfill_failure():
    # Enough balance, but fulfilment fails -> debit must be refunded, no item lost.
    res, pts, appended, seen, under = _apply(1.0, confirmations=6, pre_balance=1.0, fulfill_status="pending")
    assert res["action"] != "fulfilled_from_balance"
    assert round(pts.bal["u1"], 8) == 2.0  # 1.0 + 1.0 credit; debit refunded
