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
    monkeypatch.setattr(pay, "_treasury_stashed_usd_by_mode", lambda mode: 200.0)
    monkeypatch.setattr(pay, "_sweep_pool_usd", lambda: 200.0)
    monkeypatch.setattr(pay, "_live_enabled", lambda: False)
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    monkeypatch.delenv("EXCHANGE_AUTO_SWEEP_MIN_USD", raising=False)
    monkeypatch.delenv("EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT", raising=False)
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


def test_configure_usdt_and_usdc_deposit_wallets(payout_env, monkeypatch):
    pay = payout_env["pay"]
    vault = payout_env["vault"]
    monkeypatch.delenv("EXCHANGE_VAULT_KEY", raising=False)
    res = pay.configure_binance(
        "",
        "",
        deposit_addresses={"USDT": "TUsdtDepositAddr111", "USDC": "TUsdcDepositAddr222"},
    )
    assert res["success"] is True
    assert set(res["deposit_assets"]) == {"USDT", "USDC"}
    labels = {w["label"]: w for w in vault.list_wallets()}
    assert labels["binance_usdt"]["address"] == "TUsdtDepositAddr111"
    assert labels["binance_usdc"]["address"] == "TUsdcDepositAddr222"
    assert labels["binance_usdt"]["asset"] == "USDT"
    assert labels["binance_usdc"]["asset"] == "USDC"


def test_sync_binance_stable_wallets_paper(payout_env, monkeypatch):
    pay = payout_env["pay"]
    vault = payout_env["vault"]
    monkeypatch.delenv("EXCHANGE_VAULT_KEY", raising=False)
    res = pay.sync_binance_stable_wallets()
    assert res["success"] is True
    assets = {w["asset"] for w in res["wallets"]}
    assert assets == {"USDT", "USDC"}
    labels = {w["label"] for w in vault.list_wallets()}
    assert "binance_usdt" in labels
    assert "binance_usdc" in labels
    st = pay.binance_stable_wallets_status()
    assert st["success"] is True
    assert st["tradeable"] is True
    quoted = {w["asset"] for w in st["wallets"]}
    assert quoted == {"USDT", "USDC"}


def test_sync_binance_stable_wallets_live_addresses(payout_env, monkeypatch):
    pay = payout_env["pay"]
    vault = payout_env["vault"]
    monkeypatch.setenv("BINANCE_API_KEY", "test-key")
    monkeypatch.setenv("BINANCE_API_SECRET", "test-secret")

    def fake_deposit(coin, network="TRC20", **kwargs):
        addr = "TUsdtLiveDeposit111" if str(coin).upper() == "USDT" else "TUsdcLiveDeposit222"
        return {
            "success": True,
            "mode": "live",
            "simulated": False,
            "address": addr,
            "coin": str(coin).upper(),
            "network": "TRX",
            "tag": "",
        }

    monkeypatch.setattr(
        "backend.services.exchange_binance_withdraw_service.get_deposit_address",
        fake_deposit,
    )
    monkeypatch.setattr(
        "backend.services.exchange_binance_withdraw_service.get_spot_asset_free",
        lambda asset, **kw: {"success": True, "free": 12.5, "asset": asset},
    )
    res = pay.sync_binance_stable_wallets(dry_run=False)
    assert res["success"] is True
    by_asset = {w["asset"]: w for w in res["wallets"]}
    assert by_asset["USDT"]["address"] == "TUsdtLiveDeposit111"
    assert by_asset["USDC"]["address"] == "TUsdcLiveDeposit222"
    labels = {w["label"]: w for w in vault.list_wallets()}
    assert labels["binance_usdt"]["address"] == "TUsdtLiveDeposit111"
    assert labels["binance_usdc"]["address"] == "TUsdcLiveDeposit222"


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
