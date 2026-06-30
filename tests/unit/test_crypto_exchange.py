"""Crypto exchange unit tests."""
import json
import os
import pytest


@pytest.fixture
def ex_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    (data / "wallets").mkdir()
    cfg = tmp_path / "crypto_exchange_config.json"
    src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "crypto_exchange_config.json")
    cfg.write_text(open(src, encoding="utf-8").read(), encoding="utf-8")

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

    def _noop_emit(*args, **kwargs):
        return {"success": True}

    monkeypatch.setattr("backend.services.activity_events_service.emit", _noop_emit)
    return ex


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
    return db


def test_catalog_has_25_assets(ex_env):
    cat = ex_env.get_catalog()
    assert cat["success"] is True
    assert cat["asset_count"] == 25
    symbols = {a["symbol"] for a in cat["assets"]}
    assert "BTC" in symbols and "MN2" in symbols and "ETH" in symbols


def test_quote_swap_buy(ex_env):
    q = ex_env.quote_swap("u1", "BTC", "buy", 0.001, "MN2")
    assert q["success"] is True
    assert q["quote_cost"] > 0
    assert q["fee_bps"] >= 0


def test_execute_swap_buy_with_mn2(ex_env, points_db):
    points_db.add_points("trader1", "mn2_balance", 5000.0, source="seed", metadata={"reference": "seed"})
    q = ex_env.quote_swap("trader1", "USDC", "buy", 10.0, "MN2")
    assert q["success"] is True
    res = ex_env.execute_swap("trader1", q["quote_id"], "USDC", "buy", 10.0, "MN2")
    assert res["success"] is True, res.get("error")
    w = ex_env.get_wallet("trader1")
    assert float(w["assets"].get("USDC") or 0) >= 10.0


def test_quote_swap_usdc_to_usdt(ex_env):
    ex_env._adjust_balance("pool_user", "USDC", 100.0)
    q = ex_env.quote_swap("pool_user", "USDT", "buy", 10.0, "USDC")
    assert q["success"] is True
    assert q["quote_currency"] == "USDC"
    assert q["price_quote"] == pytest.approx(1.0, rel=0.01)
    assert q["quote_cost"] > 10.0


def test_execute_swap_usdc_to_usdt(ex_env):
    ex_env._adjust_balance("pool_user", "USDC", 100.0)
    q = ex_env.quote_swap("pool_user", "USDT", "buy", 10.0, "USDC")
    assert q["success"] is True
    res = ex_env.execute_swap("pool_user", q["quote_id"], "USDT", "buy", 10.0, "USDC")
    assert res["success"] is True, res.get("error")
    w = ex_env.get_wallet("pool_user")
    assert float(w["assets"].get("USDT") or 0) == pytest.approx(10.0, rel=1e-6)
    assert float(w["assets"].get("USDC") or 0) < 90.0


def test_execute_swap_usdt_to_usdc(ex_env):
    ex_env._adjust_balance("pool_user2", "USDT", 50.0)
    q = ex_env.quote_swap("pool_user2", "USDC", "buy", 5.0, "USDT")
    assert q["success"] is True
    res = ex_env.execute_swap("pool_user2", q["quote_id"], "USDC", "buy", 5.0, "USDT")
    assert res["success"] is True, res.get("error")
    w = ex_env.get_wallet("pool_user2")
    assert float(w["assets"].get("USDC") or 0) == pytest.approx(5.0, rel=1e-6)


def test_welcome_bonus_once(ex_env, points_db):
    r1 = ex_env.claim_welcome_bonus("bonus_user", "2026-06-v1", True)
    assert r1["success"] is True
    r2 = ex_env.claim_welcome_bonus("bonus_user", "2026-06-v1", True)
    assert r2["success"] is False
    assert r2["error"] == "already_claimed"


def test_tax_report_empty(ex_env):
    rep = ex_env.get_tax_report("nobody", 2026)
    assert rep["success"] is True
    assert rep["trade_count"] == 0


def test_user_progress_report(ex_env):
    ex_env._adjust_balance("progress_user", "USDC", 25.0)
    ex_env._add_volume("progress_user", 125.0)
    report = ex_env.get_user_progress_report("progress_user")
    assert report["success"] is True
    assert report["portfolio_value_usd"] > 0
    assert report["asset_count"] == 1
    assert report["volume_usd_30d"] == pytest.approx(125.0)
    assert "high_scores" in report
    assert report["status_items"]


def test_profit_agent_report_tracks_realized_and_unrealized_pnl(ex_env):
    from backend.services.crypto_exchange_profit_agent_service import build_profit_report

    ex_env._append_jsonl(ex_env._TRADES_PATH, {
        "ts": ex_env._iso(),
        "user_id": "profit_user",
        "symbol": "USDC",
        "side": "buy",
        "amount": 10.0,
        "usd_value": 10.0,
        "fee_usd": 0.1,
    })
    ex_env._append_jsonl(ex_env._TRADES_PATH, {
        "ts": ex_env._iso(),
        "user_id": "profit_user",
        "symbol": "USDC",
        "side": "sell",
        "amount": 4.0,
        "usd_value": 5.0,
        "fee_usd": 0.05,
    })
    ex_env._adjust_balance("profit_user", "USDC", 6.0)

    report = build_profit_report("profit_user")
    assert report["success"] is True
    assert report["trade_count"] == 2
    assert report["realized_pnl_usd"] > 0
    assert report["portfolio_value_usd"] > 0
    assert report["estimated_total_pnl_usd"] == pytest.approx(
        report["realized_pnl_usd"] + report["unrealized_pnl_usd"]
    )
    assert report["insights"]


def test_gateway_status_counts_pending_orders(ex_env):
    from backend.services.crypto_exchange_gateway_service import gateway_status

    ex_env.record_paypal_crypto_order("PAY-GW-CRYPTO", {
        "success": True,
        "user_id": "gateway_user",
        "symbol": "USDC",
        "usd_amount": 25.0,
        "fee_usd": 0.25,
        "asset_amount": 24.75,
        "expires_at": ex_env._iso(),
    })
    ex_env.record_paypal_mn2_order("PAY-GW-MN2", "gateway_user", {
        "id": "mn2-starter",
        "name": "MN2 Starter",
        "price_usd": 4.99,
        "mn2_granted": 10.0,
        "payment_rails": ["paypal"],
    })

    status = gateway_status()
    assert status["success"] is True
    assert status["gateway"]["id"] == "exchange_payment_gateway"
    assert status["totals"]["pending_count"] == 2
    assert "paypal_crypto" in status["rails"]


def test_risk_blocks_daily_cap_and_velocity(ex_env, monkeypatch):
    from backend.services import crypto_exchange_risk_service as risk

    cfg = ex_env.load_config()
    cfg["risk_limits"] = {
        "enabled": True,
        "daily_fiat_buy_usd_cap": 100.0,
        "monthly_fiat_buy_usd_cap": 1000.0,
        "velocity_max_buys_per_hour": 2,
        "blocked_countries": ["US"],
    }
    monkeypatch.setattr(ex_env, "load_config", lambda: cfg)

    assert risk.check_fiat_buy("risk_user", 50.0)["ok"] is True
    assert risk.check_fiat_buy("risk_user", 25.0, country="US")["error"] == "country_blocked"

    ex_env.record_paypal_crypto_order("R1", {
        "success": True, "user_id": "risk_user", "symbol": "USDC",
        "usd_amount": 80.0, "fee_usd": 0.5, "asset_amount": 79.5, "expires_at": ex_env._iso(),
    })
    rows = ex_env._read_json(ex_env._PAYPAL_CRYPTO_ORDERS_PATH, {})
    rows.setdefault("captured", {})["R1"] = {"user_id": "risk_user", "usd_amount": 80.0, "captured_at": ex_env._iso()}
    ex_env._write_json(ex_env._PAYPAL_CRYPTO_ORDERS_PATH, rows)

    over = risk.check_fiat_buy("risk_user", 50.0)
    assert over["ok"] is False
    assert over["error"] == "daily_cap_exceeded"


def test_audit_chain_records_and_verifies(ex_env, points_db):
    points_db.add_points("audit_trader", "mn2_balance", 5000.0, source="seed", metadata={"reference": "seed"})
    q = ex_env.quote_swap("audit_trader", "USDC", "buy", 10.0, "MN2")
    res = ex_env.execute_swap("audit_trader", q["quote_id"], "USDC", "buy", 10.0, "MN2")
    assert res["success"] is True

    tail = ex_env.get_audit_tail(limit=10)
    assert tail["count"] >= 1
    assert any(r.get("action") == "swap" for r in tail["records"])

    chain = ex_env.verify_audit_chain()
    assert chain["valid"] is True

    with open(ex_env._AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"action": "tamper", "prev_hash": "x", "hash": "y"}) + "\n")
    assert ex_env.verify_audit_chain()["valid"] is False


def test_admin_board_requires_key_and_returns_overview(ex_env, monkeypatch):
    from flask import Flask
    from backend.routes import crypto_exchange_routes as routes

    app = Flask(__name__)
    app.register_blueprint(routes.crypto_exchange_bp)
    client = app.test_client()

    monkeypatch.delenv("EXCHANGE_ADMIN_KEY", raising=False)
    monkeypatch.delenv("COGS_ADMIN_REPORT_KEY", raising=False)
    assert client.get("/api/exchange/admin/board").status_code == 401

    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", "secret-key")
    ok = client.get("/api/exchange/admin/board", headers={"X-Exchange-Admin-Key": "secret-key"})
    assert ok.status_code == 200
    body = ok.get_json()
    assert body["success"] is True
    assert "fiat_orders" in body
    assert "audit" in body


def test_exchange_routes_health():
    from flask import Flask
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    app = Flask(__name__)
    app.register_blueprint(crypto_exchange_bp)
    client = app.test_client()
    h = client.get("/api/exchange/health")
    assert h.status_code == 200
    assert h.get_json().get("service") == "crypto_exchange"
    cat = client.get("/api/exchange/catalog")
    assert cat.status_code == 200
    assert cat.get_json().get("asset_count") == 25
    progress = client.get("/api/exchange/user-progress?user_id=route_user")
    assert progress.status_code == 200
    assert progress.get_json().get("success") is True
    profit = client.get("/api/exchange/profit-agent?user_id=route_user")
    assert profit.status_code == 200
    assert profit.get_json().get("agent", {}).get("id") == "exchange_profit_oracle"
    gateway = client.get("/api/exchange/gateway/status")
    assert gateway.status_code == 200
    assert gateway.get_json().get("gateway", {}).get("id") == "exchange_payment_gateway"


def test_exchange_paypal_mn2_order_routes(ex_env, monkeypatch, points_db):
    from flask import Flask
    from backend.routes import crypto_exchange_routes as routes

    pack = {
        "id": "mn2-starter",
        "name": "MN2 Starter",
        "price_usd": 4.99,
        "mn2_granted": 10.0,
        "payment_rails": ["paypal"],
    }

    monkeypatch.setattr(routes, "_mn2_paypal_pack", lambda pack_id: pack if pack_id == "mn2-starter" else None)
    monkeypatch.setattr(
        "backend.services.paypal_service.create_order",
        lambda **kwargs: {"success": True, "order_id": "PAY-1", "approve_url": "https://paypal.test/checkout"},
    )
    monkeypatch.setattr(
        "backend.services.paypal_service.capture_order",
        lambda order_id: {
            "success": True,
            "order_id": order_id,
            "capture_id": "CAP-1",
            "amount": "4.99",
            "currency": "USD",
        },
    )

    app = Flask(__name__)
    app.register_blueprint(routes.crypto_exchange_bp)
    client = app.test_client()

    created = client.post(
        "/api/exchange/paypal/create-mn2-order",
        json={"user_id": "buyer_paypal", "pack_id": "mn2-starter"},
    )
    assert created.status_code == 200
    assert created.get_json()["approve_url"].startswith("https://paypal.test")

    captured = client.post(
        "/api/exchange/paypal/capture-mn2-order",
        json={"user_id": "buyer_paypal", "order_id": "PAY-1", "pack_id": "attacker-bigger-pack"},
    )
    assert captured.status_code == 200
    body = captured.get_json()
    assert body["success"] is True
    assert body["mn2_granted"] == pytest.approx(10.0)
    bal = points_db.get_all_points("buyer_paypal")
    assert float(bal["points"]["mn2_balance"]) >= 10.0


def test_exchange_paypal_crypto_rejects_wrong_user_and_underpay(ex_env, monkeypatch):
    from flask import Flask
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    app = Flask(__name__)
    app.register_blueprint(crypto_exchange_bp)
    client = app.test_client()

    monkeypatch.setattr(
        "backend.services.paypal_service.create_order",
        lambda **kwargs: {"success": True, "order_id": "PAY-CRYPTO-BAD", "approve_url": "https://paypal.test/crypto"},
    )
    monkeypatch.setattr(
        "backend.services.paypal_service.capture_order",
        lambda order_id: {
            "success": True,
            "order_id": order_id,
            "capture_id": "CAP-CRYPTO-BAD",
            "amount": "25.00",
            "currency": "USD",
        },
    )
    created = client.post(
        "/api/exchange/paypal/create-crypto-order",
        json={"user_id": "real_buyer", "symbol": "USDC", "usd_amount": 25.0},
    )
    assert created.status_code == 200
    wrong_user = client.post(
        "/api/exchange/paypal/capture-crypto-order",
        json={"user_id": "different_buyer", "order_id": "PAY-CRYPTO-BAD"},
    )
    assert wrong_user.status_code == 400
    assert wrong_user.get_json()["error"] == "order_user_mismatch"

    monkeypatch.setattr(
        "backend.services.paypal_service.create_order",
        lambda **kwargs: {"success": True, "order_id": "PAY-CRYPTO-UNDER", "approve_url": "https://paypal.test/crypto"},
    )
    monkeypatch.setattr(
        "backend.services.paypal_service.capture_order",
        lambda order_id: {
            "success": True,
            "order_id": order_id,
            "capture_id": "CAP-CRYPTO-UNDER",
            "amount": "1.00",
            "currency": "USD",
        },
    )
    created = client.post(
        "/api/exchange/paypal/create-crypto-order",
        json={"user_id": "real_buyer", "symbol": "USDC", "usd_amount": 25.0},
    )
    assert created.status_code == 200
    underpaid = client.post(
        "/api/exchange/paypal/capture-crypto-order",
        json={"user_id": "real_buyer", "order_id": "PAY-CRYPTO-UNDER"},
    )
    assert underpaid.status_code == 400
    assert underpaid.get_json()["error"] == "capture_amount_mismatch"


def test_exchange_paypal_crypto_order_routes(ex_env, monkeypatch):
    from flask import Flask
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    monkeypatch.setattr(
        "backend.services.paypal_service.create_order",
        lambda **kwargs: {"success": True, "order_id": "PAY-CRYPTO-1", "approve_url": "https://paypal.test/crypto"},
    )
    monkeypatch.setattr(
        "backend.services.paypal_service.capture_order",
        lambda order_id: {
            "success": True,
            "order_id": order_id,
            "capture_id": "CAP-CRYPTO-1",
            "amount": "25.00",
            "currency": "USD",
        },
    )

    app = Flask(__name__)
    app.register_blueprint(crypto_exchange_bp)
    client = app.test_client()

    created = client.post(
        "/api/exchange/paypal/create-crypto-order",
        json={"user_id": "buyer_crypto", "symbol": "USDC", "usd_amount": 25.0},
    )
    assert created.status_code == 200
    assert created.get_json()["approve_url"].startswith("https://paypal.test")

    captured = client.post(
        "/api/exchange/paypal/capture-crypto-order",
        json={"user_id": "buyer_crypto", "order_id": "PAY-CRYPTO-1"},
    )
    assert captured.status_code == 200
    body = captured.get_json()
    assert body["success"] is True
    assert body["symbol"] == "USDC"
    assert body["asset_amount"] > 0
    wallet = ex_env.get_wallet("buyer_crypto")
    assert float(wallet["assets"].get("USDC") or 0) > 0


def test_exchange_agent_tick(ex_env, points_db, tmp_path, monkeypatch):
    from backend.services import crypto_exchange_agent_service as agents

    monkeypatch.setattr(agents, "_STATE_PATH", str(tmp_path / "agent_state.json"))
    result = agents.tick(force=True)
    assert result["success"] is True
    assert result["actions"]
    assert any(a.get("success") for a in result["actions"])


def test_exchange_agent_tick_route_requires_secret(monkeypatch):
    from flask import Flask
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    monkeypatch.delenv("EXCHANGE_AGENT_SECRET", raising=False)
    app = Flask(__name__)
    app.register_blueprint(crypto_exchange_bp)
    client = app.test_client()
    no_secret = client.post("/api/exchange/agents/tick", json={"force": True})
    assert no_secret.status_code == 403

    monkeypatch.setenv("EXCHANGE_AGENT_SECRET", "secret")
    unauthorized = client.post("/api/exchange/agents/tick", json={"force": True})
    assert unauthorized.status_code == 401


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
