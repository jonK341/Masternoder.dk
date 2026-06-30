"""Live execution + treasury stash tests."""
import os
import pytest


@pytest.fixture
def live_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import exchange_treasury_service as tre
    from backend.services import exchange_live_execution_service as live
    from backend.services import exchange_secrets_vault_service as vault

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(tre, "_LEDGER_PATH", str(data / "treasury_stash.jsonl"))
    monkeypatch.setattr(tre, "_CFG_PATH", str(tmp_path / "exchange_treasury_config.json"))
    monkeypatch.setattr(vault, "_DATA_DIR", str(data))
    monkeypatch.setattr(vault, "_VAULT_PATH", str(data / "secrets_vault.enc"))
    (tmp_path / "exchange_treasury_config.json").write_text(
        '{"enabled":true,"treasury_user_id":"platform_treasury","auto_stash_on_trade":true,"min_stash_usd":0.01}',
        encoding="utf-8",
    )
    monkeypatch.delenv("EXCHANGE_ARBITRAGE_LIVE", raising=False)
    return {"ex": ex, "arb": arb, "tre": tre, "live": live}


def test_stash_profit_credits_treasury(live_env):
    tre = live_env["tre"]
    ex = live_env["ex"]
    r = tre.stash_profit_usd(10.0, source="test", agent_id="a1", mode="paper")
    assert r["success"] is True
    st = tre.treasury_status()
    assert st["ledger_stashed_usd"] >= 10.0


def test_sync_internal_prices(live_env):
    live = live_env["live"]
    injected = {
        "binance": {"BTC": {"bid": 99000, "ask": 99100, "last": 99050}},
        "nonkyc": {"BTC": {"bid": 98900, "ask": 99000, "last": 98950}},
    }
    r = live.sync_internal_prices_to_external_mid(injected)
    assert r["success"] is True
    assert r.get("count", 0) >= 1


def test_execute_spatial_paper_stashes(live_env):
    live = live_env["live"]
    opp = {
        "symbol": "BTC",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "buy_ask": 100.0,
        "sell_bid": 101.0,
        "notional_usd": 200,
        "est_profit_usd": 2.0,
        "net_bps": 100,
    }
    res = live.execute_spatial_arbitrage(opp, agent_id="test_agent")
    assert res["success"] is True
    assert res["mode"] == "paper"
    assert res.get("stash", {}).get("success") is True
