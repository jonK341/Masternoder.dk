"""MN2 / USDT / USDC liquidity pool and pool agent."""
import json
import uuid
import pytest
from flask import Flask


@pytest.fixture
def pool_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_mn2_pool_service as pool
    from backend.services import exchange_mn2_pool_agent_service as pool_agent
    from backend.routes import crypto_exchange_routes as routes

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    (data / "wallets").mkdir()
    cfg = tmp_path / "crypto_exchange_config.json"
    src = ex._CONFIG_PATH
    cfg.write_text(open(src, encoding="utf-8").read(), encoding="utf-8")

    pool_user = f"test_mn2_pool_{uuid.uuid4().hex[:8]}"
    pool_cfg = tmp_path / "exchange_mn2_pool_config.json"
    pool_cfg.write_text(json.dumps({
        "enabled": True,
        "pool_user_id": pool_user,
        "agent_id": "exchange_agent_mn2_pool",
        "reserve_user_id": f"{pool_user}_reserve",
        "pool_swap_reserve_bps": 200,
        "paper_seed_on_empty": True,
        "paper_seed": {"MN2": 5000, "USDT": 2000, "USDC": 2000},
        "min_pool_by_asset": {"MN2": 1000, "USDT": 200, "USDC": 200},
        "seed_mn2_per_tick": 100,
        "tick_cooldown_seconds": 0,
    }), encoding="utf-8")

    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(ex, "_CONFIG_PATH", str(cfg))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(data / "wallets"))
    monkeypatch.setattr(ex, "_ORDERS_PATH", str(data / "orders.json"))
    monkeypatch.setattr(ex, "_TRADES_PATH", str(data / "trades.jsonl"))
    monkeypatch.setattr(ex, "_TAX_PATH", str(data / "tax_ledger.jsonl"))
    monkeypatch.setattr(ex, "_BONUS_PATH", str(data / "bonus_claims.json"))
    monkeypatch.setattr(ex, "_TREASURY_PATH", str(data / "fee_treasury.json"))
    monkeypatch.setattr(ex, "_PRICE_CACHE_PATH", str(data / "price_cache.json"))
    monkeypatch.setattr(ex, "_PAYPAL_CRYPTO_ORDERS_PATH", str(data / "paypal_crypto_orders.json"))
    monkeypatch.setattr(ex, "_PAYPAL_MN2_ORDERS_PATH", str(data / "paypal_mn2_orders.json"))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(ex, "_mn2_usd", lambda: 0.05)
    monkeypatch.setattr(pool, "_CFG_PATH", str(pool_cfg))
    monkeypatch.setattr(pool, "_STATE_PATH", str(data / "mn2_pool_state.json"))
    monkeypatch.setattr(pool, "_LEDGER_PATH", str(data / "mn2_pool_ledger.jsonl"))
    monkeypatch.setattr(pool, "_RESERVE_PATH", str(data / "mn2_pool_reserve.json"))
    monkeypatch.setattr(pool, "_RESERVE_LEDGER_PATH", str(data / "mn2_pool_reserve_ledger.jsonl"))
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})

    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)

    def _file_only_get(user_id: str):
        return {"success": True, "points": db._points_payload_from_file(user_id)}

    monkeypatch.setattr(db, "get_all_points", _file_only_get)
    pool.ensure_paper_seed()

    app = Flask(__name__)
    app.register_blueprint(routes.crypto_exchange_bp)
    return {
        "ex": ex,
        "pool": pool,
        "pool_agent": pool_agent,
        "client": app.test_client(),
        "pool_user": pool_user,
        "points_db": db,
    }


@pytest.fixture
def points_db(pool_env):
    return pool_env["points_db"]


def test_pool_status_and_paper_seed(pool_env):
    pool = pool_env["pool"]
    st = pool.mn2_pool_status()
    assert st["success"] is True
    assert st["pool_assets"]["MN2"] > 0
    assert st["pool_assets"]["USDT"] > 0
    assert st["pool_assets"]["USDC"] > 0


def test_is_pool_swap(pool_env):
    pool = pool_env["pool"]
    assert pool.is_pool_swap("USDT", "MN2") is True
    assert pool.is_pool_swap("MN2", "USDC") is True
    assert pool.is_pool_swap("BTC", "MN2") is False
    assert pool.is_pool_swap("USDT", "USDC") is False


def test_buy_usdt_drains_pool(pool_env, points_db):
    ex = pool_env["ex"]
    pool = pool_env["pool"]
    pool.ensure_paper_seed()
    before = pool.pool_balances()["USDT"]
    points_db.add_points("buyer", "mn2_balance", 5000.0, source="seed", metadata={"reference": "seed"})
    q = ex.quote_swap("buyer", "USDT", "buy", 10.0, "MN2")
    assert q["success"] is True
    assert q.get("pool_backed") is True
    res = ex.execute_swap("buyer", q["quote_id"], "USDT", "buy", 10.0, "MN2")
    assert res["success"] is True, res.get("error")
    after = pool.pool_balances()["USDT"]
    assert after == pytest.approx(before - 10.0, rel=1e-6)


def test_sell_usdt_returns_mn2_from_pool(pool_env, points_db):
    ex = pool_env["ex"]
    pool = pool_env["pool"]
    pool.ensure_paper_seed()
    before_mn2 = pool.pool_balances()["MN2"]
    ex._adjust_balance("seller", "USDT", 25.0)
    q = ex.quote_swap("seller", "USDT", "sell", 10.0, "MN2")
    assert q["success"] is True
    res = ex.execute_swap("seller", q["quote_id"], "USDT", "sell", 10.0, "MN2")
    assert res["success"] is True, res.get("error")
    after_mn2 = pool.pool_balances()["MN2"]
    assert after_mn2 < before_mn2


def test_sell_mn2_for_usdt(pool_env, points_db):
    ex = pool_env["ex"]
    pool = pool_env["pool"]
    pool.ensure_paper_seed()
    before_usdt = pool.pool_balances()["USDT"]
    points_db.add_points("mn2_seller", "mn2_balance", 500.0, source="seed", metadata={"reference": "seed"})
    q = ex.quote_swap("mn2_seller", "MN2", "sell", 50.0, "USDT")
    assert q["success"] is True
    res = ex.execute_swap("mn2_seller", q["quote_id"], "MN2", "sell", 50.0, "USDT")
    assert res["success"] is True, res.get("error")
    w = ex.get_wallet("mn2_seller")
    assert float(w["assets"].get("USDT") or 0) > 0
    assert pool.pool_balances()["USDT"] < before_usdt


def test_swap_back_round_trip(pool_env, points_db):
    ex = pool_env["ex"]
    points_db.add_points("roundtrip", "mn2_balance", 5000.0, source="seed", metadata={"reference": "seed"})
    q1 = ex.quote_swap("roundtrip", "USDC", "buy", 5.0, "MN2")
    assert ex.execute_swap("roundtrip", q1["quote_id"], "USDC", "buy", 5.0, "MN2")["success"] is True
    q2 = ex.quote_swap("roundtrip", "USDC", "sell", 5.0, "MN2")
    assert q2["success"] is True
    res2 = ex.execute_swap("roundtrip", q2["quote_id"], "USDC", "sell", 5.0, "MN2")
    assert res2["success"] is True, res2.get("error")
    mn2_after = float(points_db.get_all_points("roundtrip")["points"]["mn2_balance"])
    assert mn2_after > 0


def test_insufficient_pool_liquidity(pool_env, points_db, monkeypatch):
    ex = pool_env["ex"]
    pool = pool_env["pool"]
    pool.ensure_paper_seed()
    uid = pool.pool_user_id()
    ex._adjust_balance(uid, "USDT", -pool.pool_balances()["USDT"])
    points_db.add_points("big_buyer", "mn2_balance", 50000.0, source="seed", metadata={"reference": "seed"})
    q = ex.quote_swap("big_buyer", "USDT", "buy", 100.0, "MN2")
    assert q["success"] is False
    assert q["error"] == "insufficient_pool_liquidity"


def test_mn2_pool_status_route(pool_env):
    res = pool_env["client"].get("/api/exchange/mn2-pool/status")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert "MN2" in body["pool_assets"]


def test_pool_swap_reserve_stashed_on_buy(pool_env, points_db):
    ex = pool_env["ex"]
    pool = pool_env["pool"]
    pool.ensure_paper_seed()
    points_db.add_points("reserve_buyer", "mn2_balance", 5000.0, source="seed", metadata={"reference": "seed"})
    q = ex.quote_swap("reserve_buyer", "USDT", "buy", 10.0, "MN2")
    assert q["success"] is True
    assert q.get("pool_reserve_bps") == 200
    assert float(q.get("pool_reserve_quote") or 0) > 0
    res = ex.execute_swap("reserve_buyer", q["quote_id"], "USDT", "buy", 10.0, "MN2")
    assert res["success"] is True, res.get("error")
    reserve = pool.reserve_balances()
    assert float(reserve.get("MN2") or 0) == pytest.approx(float(q["pool_reserve_quote"]), rel=1e-6)


def test_pool_swap_reserve_stashed_on_sell_back(pool_env, points_db):
    ex = pool_env["ex"]
    pool = pool_env["pool"]
    pool.ensure_paper_seed()
    ex._adjust_balance("reserve_seller", "USDC", 25.0)
    q = ex.quote_swap("reserve_seller", "USDC", "sell", 10.0, "MN2")
    assert q["success"] is True
    assert float(q.get("pool_reserve_quote") or 0) > 0
    before = float(pool.reserve_balances().get("MN2") or 0)
    res = ex.execute_swap("reserve_seller", q["quote_id"], "USDC", "sell", 10.0, "MN2")
    assert res["success"] is True, res.get("error")
    after = float(pool.reserve_balances().get("MN2") or 0)
    assert after > before


def test_pool_agent_tick_seeds_mn2(pool_env, monkeypatch):
    pool = pool_env["pool"]
    pool.ensure_paper_seed()
    uid = pool.pool_user_id()
    from backend.services.unified_points_database import unified_points_db

    unified_points_db.add_points(uid, "mn2_balance", -4000.0, source="test_drain", metadata={"reference": "drain"})
    result = pool.run_mn2_pool_agent_tick(force=True)
    assert result["success"] is True
    assert pool.pool_balances()["MN2"] > 0
