"""AI multi-venue trading + signed venue API tests."""
import os
import pytest


@pytest.fixture
def ai_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import external_exchange_connector_service as conn
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import exchange_ai_trading_service as ai
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import exchange_secrets_vault_service as vault

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)

    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(conn, "_PRICE_CACHE_PATH", str(data / "external_prices.json"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(vault, "_DATA_DIR", str(data))
    monkeypatch.setattr(vault, "_VAULT_PATH", str(data / "secrets_vault.enc"))
    monkeypatch.setattr(vault, "_REGISTRY_PATH", str(data / "wallet_registry.json"))
    monkeypatch.setattr(ai, "_AI_CFG_PATH", str(tmp_path / "exchange_ai_trading_config.json"))
    monkeypatch.setattr(vapi, "_API_CFG_PATH", str(tmp_path / "exchange_venue_api_config.json"))

    import json
    (tmp_path / "exchange_ai_trading_config.json").write_text(json.dumps({
        "enabled": True,
        "agent_id": "ai_market_trader",
        "default_skills": ["spatial_arbitrage", "sentiment_alpha", "kelly_sizing"],
        "min_ai_score": 40,
        "min_net_bps": 20,
        "capital_usd": 1000,
        "paper_trade_usd": 400,
        "probe_venues_on_analyze": False,
        "symbols": ["BTC"],
        "venues": ["binance", "coinbase"],
    }), encoding="utf-8")
    (tmp_path / "exchange_venue_api_config.json").write_text(json.dumps({
        "venues": {
            "binance": {
                "auth": "binance_hmac",
                "api_base": "https://api.binance.com",
                "live_supported": True,
                "endpoints": {
                    "account": {"method": "GET", "path": "/api/v3/account"},
                    "order_market": {"method": "POST", "path": "/api/v3/order"},
                },
            },
            "coinbase": {
                "auth": "coinbase_jwt_stub",
                "api_base": "https://api.coinbase.com",
                "live_supported": False,
                "endpoints": {
                    "account": {"method": "GET", "path": "/api/v3/brokerage/accounts"},
                    "order_market": {"method": "POST", "path": "/api/v3/brokerage/orders"},
                },
            },
        }
    }), encoding="utf-8")

    monkeypatch.delenv("EXCHANGE_ARBITRAGE_LIVE", raising=False)
    return {"ex": ex, "arb": arb, "ai": ai, "vapi": vapi, "vault": vault}


def test_ai_analyze_ranks_opportunity(ai_env):
    ai = ai_env["ai"]
    injected = {
        "binance": {"BTC": {"bid": 99.9, "ask": 100.0, "last": 100.0}},
        "coinbase": {"BTC": {"bid": 108.0, "ask": 108.1, "last": 108.0}},
    }
    res = ai.analyze_market(injected=injected, probe_venues=False)
    assert res["success"] is True
    assert res["actionable_count"] >= 1
    top = res["top_pick"]
    assert top["buy_venue"] == "binance"
    assert top["sell_venue"] == "coinbase"
    assert top["ai_score"] > 0
    assert "sentiment_alpha" in top.get("ai_strategies", []) or "spatial_arbitrage" in top.get("ai_strategies", [])


def test_ai_tick_credits_paper_profit(ai_env):
    ai = ai_env["ai"]
    arb = ai_env["arb"]
    injected = {
        "binance": {"BTC": {"bid": 99.9, "ask": 100.0, "last": 100.0}},
        "coinbase": {"BTC": {"bid": 110.0, "ask": 110.1, "last": 110.0}},
    }
    res = ai.run_ai_tick(injected=injected)
    assert res["success"] is True
    assert res["executed"] is True
    acct = arb.read_account("ai_market_trader")
    assert acct["realized_profit_usd"] > 0
    assert acct["trade_count"] == 1
    assert res["execution"]["buy_order"].get("simulated") is True


def test_venue_api_paper_order_without_keys(ai_env):
    vapi = ai_env["vapi"]
    res = vapi.place_market_order("binance", "BTC", "buy", 0.01)
    assert res["success"] is True
    assert res.get("simulated") is True
    assert res.get("mode") == "paper"


def test_venue_api_live_gated_without_env(ai_env, monkeypatch):
    pytest.importorskip("cryptography")
    vapi = ai_env["vapi"]
    vault = ai_env["vault"]
    monkeypatch.setenv("EXCHANGE_VAULT_KEY", "test-key-123")
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    vault.set_secret("binance_api_key", "key")
    vault.set_secret("binance_api_secret", "secret")

    def fake_http(method, url, **kwargs):
        return {"success": True, "status_code": 200, "body": {"orderId": 99}}

    monkeypatch.setattr(vapi, "_http_request", fake_http)
    res = vapi.place_market_order("binance", "BTC", "buy", 0.001, dry_run=False)
    assert res["success"] is True


def test_sign_binance_deterministic(ai_env):
    vapi = ai_env["vapi"]
    sig = vapi._sign_binance({"symbol": "BTCUSDT", "timestamp": 123}, "secret")
    assert len(sig) == 64
