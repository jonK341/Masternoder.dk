"""Cross-venue arbitrage: connector, scanner, paper agents, and vault tests."""
import os
import pytest


@pytest.fixture
def arb_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import external_exchange_connector_service as conn
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import exchange_secrets_vault_service as vault

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)

    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(conn, "_PRICE_CACHE_PATH", str(data / "external_prices.json"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(vault, "_DATA_DIR", str(data))
    monkeypatch.setattr(vault, "_VAULT_PATH", str(data / "secrets_vault.enc"))
    monkeypatch.setattr(vault, "_REGISTRY_PATH", str(data / "wallet_registry.json"))

    return {"ex": ex, "conn": conn, "arb": arb, "vault": vault}


def test_list_venues_has_major_connections(arb_env):
    venues = arb_env["conn"].list_venues()
    assert venues["success"] is True
    assert venues["venue_count"] >= 20
    ids = {v["id"] for v in venues["venues"]}
    assert {"binance", "coinbase", "nonkyc", "bingx", "upbit", "poloniex"}.issubset(ids)


def test_build_pair_applies_overrides_and_templates(arb_env):
    conn = arb_env["conn"]
    vmap = conn._venue_map()
    assert conn.build_pair(vmap["binance"], "BTC") == "BTCUSDC"
    assert conn.build_pair(vmap["binance"], "DOGE") == "DOGEUSDC"
    assert conn.build_pair(vmap["coinbase"], "BTC") == "BTC-USD"
    assert conn.build_pair(vmap["nonkyc"], "BTC") == "BTC_USDT"
    assert conn.build_pair(vmap["bitstamp"], "BTC") == "btcusd"  # lowercase
    assert conn.build_pair(vmap["upbit"], "BTC") == "USDT-BTC"


def test_parsers_normalize_each_venue_shape(arb_env):
    conn = arb_env["conn"]
    assert conn._p_binance({"bidPrice": "100", "askPrice": "101"})["bid"] == 100.0
    assert conn._p_coinbase({"bid": "100", "ask": "101", "price": "100.5"})["last"] == 100.5
    assert conn._p_kraken({"result": {"XXBTZUSD": {"a": ["101"], "b": ["100"], "c": ["100.5"]}}})["ask"] == 101.0
    assert conn._p_nonkyc({"bid": "100", "ask": "101", "last_price": "100.5"})["last"] == 100.5
    assert conn._p_bitfinex([100, 1, 101, 1, 0, 0, 100.5, 0, 0, 0])["bid"] == 100.0
    assert conn._p_gateio([{"highest_bid": "100", "lowest_ask": "101", "last": "100.5"}])["ask"] == 101.0
    assert conn._p_bingx({"data": {"bidPrice": "100", "askPrice": "101"}})["bid"] == 100.0
    assert conn._p_poloniex({"bid": "100", "ask": "101", "close": "100.5"})["ask"] == 101.0
    assert conn._p_bitmart({"data": {"bid_px": "100", "ask_px": "101", "last": "100.5"}})["bid"] == 100.0
    assert conn._p_coinex({"data": {"ticker": {"buy": "100", "sell": "101", "last": "100.5"}}})["bid"] == 100.0
    assert conn._p_upbit([{"orderbook_units": [{"bid_price": 100, "ask_price": 101}]}])["ask"] == 101.0
    assert conn._p_xt({"result": [{"bp": "100", "ap": "101", "c": "100.5"}]})["bid"] == 100.0


def test_scan_finds_profitable_spread(arb_env):
    arb = arb_env["arb"]
    injected = {
        "binance": {"BTC": {"bid": 99.9, "ask": 100.0, "last": 100.0}},
        "coinbase": {"BTC": {"bid": 105.0, "ask": 105.1, "last": 105.0}},
    }
    res = arb.scan_opportunities(["BTC"], ["binance", "coinbase"], injected=injected)
    assert res["success"] is True
    assert res["opportunity_count"] == 1
    opp = res["opportunities"][0]
    assert opp["buy_venue"] == "binance"
    assert opp["sell_venue"] == "coinbase"
    assert opp["net_bps"] > 0
    assert opp["profitable"] is True


def test_run_paper_tick_credits_agent_account(arb_env):
    arb = arb_env["arb"]
    # Wide spread on BTC across the btc/eth agent's venues.
    injected = {
        "binance": {"BTC": {"bid": 99.9, "ask": 100.0, "last": 100.0}},
        "coinbase": {"BTC": {"bid": 108.0, "ask": 108.1, "last": 108.0}},
        "nonkyc": {"BTC": {"bid": 101.0, "ask": 101.2, "last": 101.0}},
        "bitstamp": {"BTC": {"bid": 100.5, "ask": 100.6, "last": 100.5}},
    }
    res = arb.run_paper_tick(injected=injected)
    assert res["success"] is True
    assert res["executed_count"] >= 1

    accounts = arb.agent_accounts()
    btc_eth = next(a for a in accounts["accounts"] if a["agent_id"] == "arb_agent_btc_eth")
    assert btc_eth["realized_profit_usd"] > 0
    assert btc_eth["trade_count"] == 1
    assert accounts["total_realized_profit_usd"] > 0


def test_wallet_registry_stores_public_addresses(arb_env):
    vault = arb_env["vault"]
    r = vault.register_wallet("arb_btc_eth_wallet", "bc1qexampleaddress", venue="binance", asset="BTC")
    assert r["success"] is True
    wallets = vault.list_wallets()
    assert any(w["label"] == "arb_btc_eth_wallet" and w["address"] == "bc1qexampleaddress" for w in wallets)


def test_secret_write_refused_without_key(arb_env, monkeypatch):
    vault = arb_env["vault"]
    monkeypatch.delenv("EXCHANGE_VAULT_KEY", raising=False)
    r = vault.set_secret("binance_api_key", "supersecret")
    assert r["success"] is False
    assert r["error"] == "encryption_unavailable"


def test_secret_roundtrip_with_key(arb_env, monkeypatch):
    pytest.importorskip("cryptography")
    vault = arb_env["vault"]
    monkeypatch.setenv("EXCHANGE_VAULT_KEY", "test-passphrase-123")
    assert vault.encryption_available() is True
    assert vault.set_secret("binance_api_key", "supersecret")["success"] is True
    assert vault.get_secret("binance_api_key") == "supersecret"
    assert "binance_api_key" in vault.list_secret_names()
