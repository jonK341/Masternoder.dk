"""Binance profit-stash (payout) service + boost scenarios."""
import pytest


@pytest.fixture
def payout_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_secrets_vault_service as vault
    from backend.services import exchange_payout_service as pay

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    wallets = data / "wallets"
    wallets.mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(wallets))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.delenv("EXCHANGE_PAYOUT_PAYPAL_EMAIL", raising=False)
    monkeypatch.setattr(vault, "_DATA_DIR", str(data))
    monkeypatch.setattr(vault, "_VAULT_PATH", str(data / "secrets_vault.enc"))
    monkeypatch.setattr(vault, "_REGISTRY_PATH", str(data / "wallet_registry.json"))
    monkeypatch.setattr(pay, "_PAYOUT_PATH", str(data / "payout_config.json"))
    monkeypatch.setattr(pay, "_SWEEPS_PATH", str(data / "payout_sweeps.jsonl"))
    monkeypatch.setattr(pay, "_realized_total_usd", lambda: 200.0)
    monkeypatch.setattr(pay, "_live_enabled", lambda: False)
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    monkeypatch.delenv("EXCHANGE_PAYOUT_BINANCE_ADDRESS", raising=False)
    return {"ex": ex, "vault": vault, "pay": pay}


def test_configure_addresses_without_keys(payout_env, monkeypatch):
    pay = payout_env["pay"]
    monkeypatch.delenv("EXCHANGE_VAULT_KEY", raising=False)
    res = pay.configure_binance("", "", deposit_addresses={"USDT": "TBinanceUSDTaddr"})
    assert res["success"] is True
    assert "USDT" in res["deposit_assets"]
    st = pay.payout_status()
    assert st["binance"]["deposit_assets"] == ["USDT"]
    assert st["binance"]["keys_present"] is False


def test_configure_with_keys_in_vault(payout_env, monkeypatch):
    pytest.importorskip("cryptography")
    pay = payout_env["pay"]
    monkeypatch.setenv("EXCHANGE_VAULT_KEY", "stash-pass-123")
    res = pay.configure_binance("APIKEY123", "SECRET456", deposit_addresses={"USDT": "TBinanceUSDTaddr"})
    assert res["success"] is True
    assert res["connected"] is True
    st = pay.payout_status()
    assert st["binance"]["keys_present"] is True
    assert st["binance"]["connected"] is True


def test_plan_and_execute_sweep(payout_env):
    pay = payout_env["pay"]
    pay.configure_binance("", "", deposit_addresses={"USDT": "TBinanceUSDTaddr"})

    plan = pay.plan_sweep()
    assert plan["actionable"] is True
    assert plan["amount_usd"] == 200.0
    assert plan["mode"] == "paper"

    ex_res = pay.execute_sweep()
    assert ex_res["success"] is True
    assert ex_res["swept_total_usd"] == 200.0

    st = pay.payout_status()
    assert st["net_unswept_usd"] == 0.0  # all swept
    after = pay.plan_sweep()
    assert after["actionable"] is False
    assert after["reason"] == "below_min_sweep"


def test_plan_blocked_without_address(payout_env, monkeypatch):
    pay = payout_env["pay"]
    monkeypatch.setattr(pay, "_owner_paypal_email", lambda cfg=None: "")
    cfg = pay._load()
    cfg["destination"] = "binance"
    pay._save(cfg)
    plan = pay.plan_sweep()
    assert plan["actionable"] is False
    assert plan["reason"] == "no_deposit_address"


def test_boost_scenarios_increase_profit():
    from backend.services.exchange_profit_tools_service import boost_scenarios
    res = boost_scenarios(2000, ["spatial_arbitrage", "triangular_arbitrage"])
    assert res["success"] is True
    names = [s["name"] for s in res["scenarios"]]
    assert names == ["Conservative", "Standard", "Boosted (Premium)", "Max Overdrive"]
    std = next(s for s in res["scenarios"] if s["name"] == "Standard")
    boosted = next(s for s in res["scenarios"] if s["name"] == "Max Overdrive")
    assert boosted["daily_profit_usd"] > std["daily_profit_usd"]
