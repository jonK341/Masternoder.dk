"""P2P MN2↔coins market tests."""
import pytest


@pytest.fixture
def market_files(tmp_path, monkeypatch):
    from backend.services import p2p_market_service as pm

    orders = tmp_path / "orders.json"
    trades = tmp_path / "trades.jsonl"
    monkeypatch.setattr(pm, "_ORDERS", str(orders))
    monkeypatch.setattr(pm, "_TRADES", str(trades))

    def _noop_emit(*args, **kwargs):
        return {"success": True}

    monkeypatch.setattr("backend.services.activity_events_service.emit", _noop_emit)
    return orders, trades


@pytest.fixture
def points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)

    def _file_only_get(user_id: str):
        return {"success": True, "points": db._points_payload_from_file(user_id)}

    monkeypatch.setattr(db, "get_all_points", _file_only_get)

    def _noop_append(*args, **kwargs):
        return {"success": True}

    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", _noop_append)
    return db


def test_create_sell_order_locks_mn2(market_files, points_db):
    from backend.services import p2p_market_service as pm

    points_db.add_points("seller1", "mn2_balance", 10.0, source="seed", metadata={"reference": "seed-seller"})
    r = pm.create_order("seller1", "sell", 2.0, 50.0)
    assert r.get("success") is True
    bal = points_db.get_all_points("seller1")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(8.0, rel=1e-6)


def test_fill_order_transfers_coins(market_files, points_db):
    from backend.services import p2p_market_service as pm

    points_db.add_points("seller2", "mn2_balance", 5.0, source="seed", metadata={"reference": "seed-s2"})
    points_db.add_points("buyer2", "coins", 1000.0, source="seed", metadata={"reference": "seed-b2"})
    created = pm.create_order("seller2", "sell", 1.0, 100.0)
    oid = created["order"]["order_id"]
    filled = pm.fill_order("buyer2", oid)
    assert filled.get("success") is True
    seller = points_db.get_all_points("seller2")
    buyer = points_db.get_all_points("buyer2")
    assert float(buyer["points"]["mn2_balance"]) >= 1.0
    assert float(seller["points"]["coins"]) >= 100.0


def test_cancel_order_unlocks_mn2(market_files, points_db):
    from backend.services import p2p_market_service as pm

    points_db.add_points("seller3", "mn2_balance", 3.0, source="seed", metadata={"reference": "seed-s3"})
    created = pm.create_order("seller3", "sell", 1.5, 80.0)
    oid = created["order"]["order_id"]
    cancelled = pm.cancel_order("seller3", oid)
    assert cancelled.get("success") is True
    bal = points_db.get_all_points("seller3")
    assert float(bal["points"]["mn2_balance"]) == pytest.approx(3.0, rel=1e-6)


def test_market_routes_ticker_and_orders():
    from flask import Flask
    from backend.routes.p2p_market_routes import p2p_market_bp

    app = Flask(__name__)
    app.register_blueprint(p2p_market_bp)
    client = app.test_client()
    cfg = client.get("/api/market/config")
    assert cfg.status_code == 200
    assert cfg.get_json().get("success") is True
    ticker = client.get("/api/market/ticker")
    assert ticker.status_code == 200
    assert ticker.get_json().get("success") is True
    orders = client.get("/api/market/orders?limit=5")
    assert orders.status_code == 200
    assert orders.get_json().get("success") is True
    trades = client.get("/api/market/trades?limit=5")
    assert trades.status_code == 200
    assert trades.get_json().get("success") is True
