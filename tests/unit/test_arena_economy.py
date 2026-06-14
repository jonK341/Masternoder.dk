"""
Unit tests for the Arena income engine (escrow + rake + payout).
Run: python -m pytest tests/unit/test_arena_economy.py -q

Verifies the core money invariant:
    sum(buy_ins) == sum(prize_payouts) + house_take   (per event, per currency)
plus the real-money security gate and refund behavior.
"""
import os
import tempfile

import pytest

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

import backend.services.arena_economy as econ


@pytest.fixture
def fake_money(monkeypatch):
    """In-memory balances + ledger, isolated escrow state file."""
    balances = {}
    ledger = []

    def _apply(user_id, delta, currency, game, meta):
        balances[(user_id, currency)] = balances.get((user_id, currency), 0.0) + float(delta)

    def _bal(user_id, currency):
        return balances.get((user_id, currency), 0.0)

    import backend.services.casino_service as cs
    monkeypatch.setattr(cs, "_apply_balance_delta", _apply)
    monkeypatch.setattr(cs, "_user_balance", _bal)
    monkeypatch.setattr(cs, "_append_ledger", lambda row: ledger.append(row))
    monkeypatch.setattr(cs, "_currency_label", lambda c: c)

    f = tempfile.NamedTemporaryFile(prefix="arena_state_", suffix=".json", delete=False)
    path = f.name
    f.close()
    os.unlink(path)
    monkeypatch.setattr(econ, "_state_path", lambda: path)

    def _credit(user_id, currency, amount):
        balances[(user_id, currency)] = balances.get((user_id, currency), 0.0) + amount

    yield {"balances": balances, "ledger": ledger, "credit": _credit}

    try:
        if os.path.isfile(path):
            os.unlink(path)
    except OSError:
        pass


def test_buy_in_debits_and_escrows(fake_money):
    fake_money["credit"]("alice", "coins", 1000)
    res = econ.collect_buy_in("alice", 250, "coins", "tournament", event_id="t1")
    assert res["success"] is True
    assert fake_money["balances"][("alice", "coins")] == 750
    ev = econ.get_event("t1")
    assert ev["pot"] == 250 and ev["buy_ins"] == 250


def test_insufficient_balance_rejected(fake_money):
    fake_money["credit"]("bob", "coins", 100)
    res = econ.collect_buy_in("bob", 250, "coins", "tournament", event_id="t2")
    assert res["success"] is False
    assert "Insufficient" in res["error"]
    assert fake_money["balances"][("bob", "coins")] == 100


def test_real_money_gate_blocks_unverified(fake_money, monkeypatch):
    fake_money["credit"]("carol", "usd", 100)

    monkeypatch.setattr(
        "backend.services.account_security_service.check_real_money_action",
        lambda user_id, verification_token=None: "Verification required",
    )
    res = econ.collect_buy_in("carol", 5.0, "usd", "tournament", event_id="t3")
    assert res["success"] is False
    assert res["error"] == "Verification required"
    assert fake_money["balances"][("carol", "usd")] == 100  # untouched


def test_rake_split_conserves(fake_money):
    prize, house = econ.split_rake(1000, 10.0, "coins")
    assert prize == 900 and house == 100
    assert prize + house == 1000


def test_event_conservation_after_settle(fake_money):
    # Three players buy in at 100 coins each -> pot 300.
    for u in ("p1", "p2", "p3"):
        fake_money["credit"](u, "coins", 100)
        assert econ.collect_buy_in(u, 100, "coins", "tournament", event_id="e1")["success"]

    ev = econ.get_event("e1")
    assert ev["buy_ins"] == 300

    prize_pool, house_take = econ.split_rake(ev["pot"], 10.0, "coins")
    assert prize_pool == 270 and house_take == 30
    econ.record_house_take(house_take, "coins", "tournament", event_id="e1")

    # Winner takes the whole prize pool.
    econ.payout("p1", prize_pool, "coins", "tournament", meta={"event_id": "e1"})

    # Manually record prizes_paid for reconcile (settle route does this).
    state = econ._load_state()
    state["events"]["e1"]["prizes_paid"] = prize_pool
    econ._save_state(state)

    rec = econ.reconcile("e1")
    assert rec["balanced"] is True
    assert fake_money["balances"][("p1", "coins")] == 270


def test_refund_is_idempotent(fake_money):
    fake_money["credit"]("dave", "coins", 500)
    entry = econ.collect_buy_in("dave", 200, "coins", "pvp", event_id="d1")
    assert fake_money["balances"][("dave", "coins")] == 300

    r1 = econ.refund_entry(entry["entry_id"])
    assert r1["success"] is True
    assert fake_money["balances"][("dave", "coins")] == 500

    r2 = econ.refund_entry(entry["entry_id"])  # replay
    assert r2.get("already") == "refunded"
    assert fake_money["balances"][("dave", "coins")] == 500  # not double-refunded


# --- route-level flow: buy-in -> settle on the battle blueprint ---

class _PointsStore:
    def __init__(self):
        self.p = {}

    def add_points(self, user_id, point_type, amount, source=None, metadata=None):
        self.p.setdefault(user_id, {})
        self.p[user_id][point_type] = self.p[user_id].get(point_type, 0) + float(amount)
        return {"success": True}

    def get_all_points(self, user_id):
        return {"points": self.p.get(user_id, {})}


@pytest.fixture
def arena_app(monkeypatch):
    import shutil
    from flask import Flask
    from unittest.mock import patch
    from backend.routes.battle_routes import battle_bp

    tmp_dir = tempfile.mkdtemp(prefix="arena_app_")
    monkeypatch.setenv("MASTERNODER_LOG_DIR", os.path.join(tmp_dir, "logs"))
    monkeypatch.setattr(econ, "_state_path", lambda: os.path.join(tmp_dir, "arena_state.json"))

    store = _PointsStore()
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(battle_bp)

    p1 = patch("backend.services.unified_points_database.unified_points_db", store)
    p1.start()
    monkeypatch.setattr(
        "backend.services.casino_service.unified_points_db", store, raising=False
    )
    yield app, store
    p1.stop()
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_route_buy_in_then_settle_conserves(arena_app):
    app, store = arena_app
    store.add_points("alice", "coins", 1000)
    store.add_points("bob", "coins", 1000)

    with app.test_client() as client:
        r1 = client.post("/api/battle/tournaments/cup1/buy-in",
                         json={"user_id": "alice", "amount": 100, "currency": "coins"})
        r2 = client.post("/api/battle/tournaments/cup1/buy-in",
                         json={"user_id": "bob", "amount": 100, "currency": "coins"})
        assert r1.status_code == 200 and r1.get_json()["success"]
        assert r2.status_code == 200 and r2.get_json()["success"]
        assert store.get_all_points("alice")["points"]["coins"] == 900

        settle = client.post("/api/battle/tournaments/cup1/settle",
                             json={"winners": ["alice", "bob"], "prize_split": [0.7, 0.3]})
        body = settle.get_json()
        assert settle.status_code == 200 and body["success"]
        # pot 200, rake 10% -> house 20, prize pool 180
        assert body["house_take"] == 20
        assert body["prize_pool"] == 180
        assert body["reconcile"]["balanced"] is True
        # alice gets 180*0.7=126 on top of 900 -> 1026
        assert store.get_all_points("alice")["points"]["coins"] == 1026

        # settle replay is idempotent (no double payout)
        again = client.post("/api/battle/tournaments/cup1/settle",
                           json={"winners": ["alice", "bob"]})
        assert again.get_json().get("already_settled") is True
        assert store.get_all_points("alice")["points"]["coins"] == 1026


def test_route_buy_in_rejects_bad_tier(arena_app):
    app, store = arena_app
    store.add_points("eve", "coins", 1000)
    with app.test_client() as client:
        r = client.post("/api/battle/tournaments/cup2/buy-in",
                       json={"user_id": "eve", "amount": 137, "currency": "coins"})
        assert r.status_code == 400
        assert "tier" in r.get_json()["error"].lower()
