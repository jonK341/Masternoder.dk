"""Multi-asset pool withdraw (Binance + NonKYC) and per-asset target config."""
import pytest


PRICES = {"BTC": 60000.0, "ETH": 3000.0, "ADA": 0.5, "SOL": 150.0,
          "USDT": 1.0, "USDC": 1.0, "AVAX": 30.0, "DASH": 25.0}


@pytest.fixture
def env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_binance_withdraw_service as bwd
    from backend.services import exchange_nonkyc_withdraw_service as nk
    from backend.services import exchange_payout_service as pay
    from backend.services import exchange_sales_pool_service as pool

    data = tmp_path / "crypto_exchange"
    wallets = data / "wallets"
    wallets.mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(wallets))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(ex, "_price_usd", lambda sym, cfg=None: PRICES.get(str(sym).upper(), 0.0))
    monkeypatch.setattr(pay, "_PAYOUT_PATH", str(data / "payout_config.json"))
    monkeypatch.setattr(pay, "_SWEEPS_PATH", str(data / "payout_sweeps.jsonl"))
    monkeypatch.setattr(pool, "_STATE_PATH", str(data / "sales_pool_state.json"))
    monkeypatch.setattr(pool, "_LEDGER_PATH", str(data / "sales_pool_ledger.jsonl"))

    cfg_path = tmp_path / "exchange_sales_pool_config.json"
    cfg_path.write_text(
        '{"enabled": true, "sales_pool_user_id": "exchange_sales_pool", "source_agent_ids": []}',
        encoding="utf-8",
    )
    monkeypatch.setattr(pool, "_CFG_PATH", str(cfg_path))

    monkeypatch.setenv("BINANCE_API_KEY", "test-key-abc")
    monkeypatch.setenv("BINANCE_API_SECRET", "test-secret-xyz")
    for flag in ("EXCHANGE_PAYOUT_BINANCE_LIVE", "EXCHANGE_ARBITRAGE_LIVE",
                 "EXCHANGE_PAYOUT_NONKYC_LIVE"):
        monkeypatch.delenv(flag, raising=False)

    return {"ex": ex, "bwd": bwd, "nk": nk, "pay": pay, "pool": pool}


def test_withdraw_asset_paper_any_coin(env):
    bwd = env["bwd"]
    res = bwd.withdraw_asset("BTC", 0.01, "bc1qexampleaddressxxxxxxxxxx", "BTC")
    assert res["success"] is True
    assert res["mode"] == "paper"
    assert res["coin"] == "BTC"
    assert res["amount"] == 0.01
    assert "withdraw_id" in res


def test_configure_and_withdraw_pool_btc_paper(env):
    ex, pay, pool = env["ex"], env["pay"], env["pool"]
    pool_uid = pool.sales_pool_user_id()
    ex._adjust_balance(pool_uid, "BTC", 0.05)

    cfg = pay.configure_venue_withdraw("binance", {
        "BTC": {"address": "bc1qBTCexampleaddr1234567890", "network": "BTC"},
    })
    assert cfg["success"] is True
    assert "BTC" in cfg["configured_coins"]

    res = pay.withdraw_pool_asset("BTC", 0.02, venue="binance")
    assert res["success"] is True
    assert res["live"] is False
    assert res["withdrawn"]["coin"] == "BTC"
    assert res["withdrawn"]["amount"] == 0.02
    assert res["pool_balance_after"] == pytest.approx(0.03)
    assert float(ex.get_wallet(pool_uid)["assets"]["BTC"]) == pytest.approx(0.03)


def test_withdraw_pool_asset_insufficient(env):
    ex, pay, pool = env["ex"], env["pay"], env["pool"]
    pool_uid = pool.sales_pool_user_id()
    ex._adjust_balance(pool_uid, "ETH", 0.001)
    pay.configure_venue_withdraw("binance", {"ETH": {"address": "0xETHaddr1234567890", "network": "ETH"}})
    res = pay.withdraw_pool_asset("ETH", 1.0, venue="binance")
    assert res["success"] is False
    assert res["error"] == "insufficient_sales_pool_balance"


def test_withdraw_pool_asset_missing_target(env):
    ex, pay, pool = env["ex"], env["pay"], env["pool"]
    ex._adjust_balance(pool.sales_pool_user_id(), "SOL", 10.0)
    res = pay.withdraw_pool_asset("SOL", 1.0, venue="binance")
    assert res["success"] is False
    assert res["error"] == "missing_withdraw_target"


def test_withdraw_pool_asset_nonkyc_paper(env):
    ex, pay, pool = env["ex"], env["pay"], env["pool"]
    pool_uid = pool.sales_pool_user_id()
    ex._adjust_balance(pool_uid, "ADA", 1000.0)
    pay.configure_venue_withdraw("nonkyc", {"ADA": {"address": "AdaNonKycAddr1234567890", "ticker": "ADA"}})
    res = pay.withdraw_pool_asset("ADA", 500.0, venue="nonkyc")
    assert res["success"] is True
    assert res["venue"] == "nonkyc"
    assert res["live"] is False
    assert float(ex.get_wallet(pool_uid)["assets"]["ADA"]) == pytest.approx(500.0)


def test_nonkyc_withdraw_service_paper(env):
    nk = env["nk"]
    res = nk.withdraw_asset("USDT", 100.0, "TnonkycUSDTaddr1234567890", venue="nonkyc")
    assert res["success"] is True
    assert res["mode"] == "paper"
    assert res["coin"] == "USDT"
    assert res["venue"] == "nonkyc"


def test_binance_multi_asset_preflight_success(env, monkeypatch):
    bwd = env["bwd"]
    addr = "bc1qBTCexampleaddr1234567890"
    monkeypatch.setattr(bwd, "get_spot_asset_free",
                        lambda coin, **k: {"success": True, "free": 1.0, "asset": coin})
    monkeypatch.setattr(bwd, "get_capital_config",
                        lambda **k: {"success": True,
                                     "body": [{"coin": "BTC",
                                               "networkList": [{"network": "BTC", "withdrawFee": "0.0002"}]}]})
    monkeypatch.setattr(bwd, "get_withdraw_address_list",
                        lambda coin="USDT", **k: {"success": True,
                                                  "addresses": [{"address": addr, "network": "BTC"}]})
    pf = bwd.preflight_withdraw_asset("BTC", 0.01, addr, "BTC")
    assert pf["ready"] is True
    assert pf["coin"] == "BTC"
    assert pf["network_fee"] == pytest.approx(0.0002)


def test_asset_preflight_status_via_payout(env, monkeypatch):
    ex, pay, pool, bwd = env["ex"], env["pay"], env["pool"], env["bwd"]
    ex._adjust_balance(pool.sales_pool_user_id(), "BTC", 0.02)
    pay.configure_venue_withdraw("binance", {"BTC": {"address": "bc1qBTCaddr1234567890", "network": "BTC"}})
    monkeypatch.setattr(bwd, "get_spot_asset_free", lambda coin, **k: {"success": True, "free": 0.0, "asset": coin})
    monkeypatch.setattr(bwd, "get_capital_config", lambda **k: {"success": True, "body": []})
    monkeypatch.setattr(bwd, "get_withdraw_address_list", lambda coin="USDT", **k: {"success": True, "addresses": []})
    out = pay.asset_preflight_status("BTC", venue="binance", amount=0.01)
    assert out["success"] is True
    assert out["coin"] == "BTC"
    assert out["sales_pool_balance"] == pytest.approx(0.02)
    assert out["preflight"]["ready"] is False
