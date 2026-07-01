"""Binance capital withdraw + sales-pool payout wiring."""
import pytest


@pytest.fixture
def binance_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_binance_withdraw_service as bwd
    from backend.services import exchange_payout_service as pay
    from backend.services import exchange_sales_pool_service as pool

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    wallets = data / "wallets"
    wallets.mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(wallets))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
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
    monkeypatch.delenv("EXCHANGE_PAYOUT_BINANCE_LIVE", raising=False)
    monkeypatch.delenv("EXCHANGE_ARBITRAGE_LIVE", raising=False)

    return {"ex": ex, "bwd": bwd, "pay": pay, "pool": pool}


def test_sign_and_withdraw_paper(binance_env):
    bwd = binance_env["bwd"]
    res = bwd.withdraw_usdt(100.0, "TTestAddress1234567890", "TRC20")
    assert res["success"] is True
    assert res["mode"] == "paper"
    assert res["simulated"] is True
    assert res["network"] == "TRX"
    assert res["address_masked"].startswith("TTes")
    assert "withdraw_id" in res


def test_network_mapping(binance_env):
    bwd = binance_env["bwd"]
    assert bwd.binance_network_code("BEP20") == "BSC"
    assert bwd.binance_network_code("ERC20") == "ETH"


def test_mask_address(binance_env):
    bwd = binance_env["bwd"]
    assert bwd.mask_address("short") == "****"
    masked = bwd.mask_address("TBinanceUSDTaddr1234567890")
    assert masked.startswith("TBin")
    assert masked.endswith("7890")


def test_withdraw_apply_live_mocked(binance_env, monkeypatch):
    bwd = binance_env["bwd"]
    monkeypatch.setenv("EXCHANGE_PAYOUT_BINANCE_LIVE", "1")
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    monkeypatch.setattr(bwd, "binance_withdraw_live_enabled", lambda: True)

    captured = {}

    def fake_http(method, url, *, headers=None, data=None, timeout=12.0):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        assert "signature=" in url
        assert headers.get("X-MBX-APIKEY") == "test-key-abc"
        return {"success": True, "status_code": 200, "body": {"id": "withdraw-999"}}

    monkeypatch.setattr(bwd, "_http_request", fake_http)
    res = bwd.withdraw_usdt(50.5, "TAddr123456789012345678901234567890", "TRC20", dry_run=False)
    assert res["success"] is True
    assert res["mode"] == "live"
    assert res["withdraw_id"] == "withdraw-999"
    assert captured["method"] == "POST"
    assert "/sapi/v1/capital/withdraw/apply" in captured["url"]
    assert "coin=USDT" in captured["url"]
    assert "network=TRX" in captured["url"]


def test_get_capital_config_mocked(binance_env, monkeypatch):
    bwd = binance_env["bwd"]

    def fake_http(method, url, *, headers=None, data=None, timeout=12.0):
        return {"success": True, "status_code": 200, "body": [{"coin": "USDT", "networkList": []}]}

    monkeypatch.setattr(bwd, "_http_request", fake_http)
    monkeypatch.setattr(bwd, "binance_withdraw_live_enabled", lambda: True)
    res = bwd.get_capital_config(dry_run=False)
    assert res["success"] is True


def test_configure_binance_withdraw_address(binance_env):
    pay = binance_env["pay"]
    res = pay.configure_binance("", "", withdraw_address="TBinanceUSDTaddr1234567890", network="TRC20")
    assert res["success"] is True
    assert res["withdraw_enabled"] is True
    assert "..." in res["withdraw_address_masked"]
    st = pay.payout_status()
    assert st["binance"]["wired"] is True
    assert st["binance"]["withdraw_network"] == "TRC20"
    assert "..." in st["binance"]["withdraw_address_masked"]


def test_withdraw_binance_paper_debits_sales_pool(binance_env):
    ex = binance_env["ex"]
    pay = binance_env["pay"]
    pool = binance_env["pool"]

    pool_uid = pool.sales_pool_user_id()
    ex._adjust_balance(pool_uid, "USDT", 500.0)
    pay.configure_binance("", "", withdraw_address="TBinanceUSDTaddr1234567890", network="TRC20")

    res = pay.withdraw_binance(100.0, min_amount=5.0)
    assert res["success"] is True
    assert res["live"] is False
    assert res["withdrawn"]["mode"] == "paper"
    assert res["withdrawn"]["amount_usdt"] == 100.0
    assert res["pool_usdt_after"] == 400.0

    wallet = ex.get_wallet(pool_uid)
    assert float(wallet["assets"]["USDT"]) == 400.0


def test_withdraw_binance_insufficient_pool(binance_env):
    pay = binance_env["pay"]
    pay.configure_binance("", "", withdraw_address="TBinanceUSDTaddr1234567890", network="TRC20")
    res = pay.withdraw_binance(50.0)
    assert res["success"] is False
    assert res["error"] == "insufficient_sales_pool_usdt"


def test_withdraw_binance_daily_cap(binance_env):
    ex = binance_env["ex"]
    pay = binance_env["pay"]
    pool = binance_env["pool"]

    pool_uid = pool.sales_pool_user_id()
    ex._adjust_balance(pool_uid, "USDT", 1000.0)
    pay.configure_binance(
        "",
        "",
        withdraw_address="TBinanceUSDTaddr1234567890",
        network="TRC20",
        max_withdraw_per_day=100.0,
    )

    ok = pay.withdraw_binance(80.0, min_amount=5.0)
    assert ok["success"] is True

    blocked = pay.withdraw_binance(50.0, min_amount=5.0)
    assert blocked["success"] is False
    assert blocked["error"] == "daily_cap_exceeded"


def test_withdraw_usdt_error_passthrough(binance_env, monkeypatch):
    bwd = binance_env["bwd"]
    monkeypatch.setenv("EXCHANGE_PAYOUT_BINANCE_LIVE", "1")
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    monkeypatch.setattr(bwd, "binance_withdraw_live_enabled", lambda: True)

    def fake_http(method, url, *, headers=None, data=None, timeout=12.0):
        return {
            "success": False,
            "status_code": 400,
            "body": {"code": -4022, "msg": "Address not in whitelist"},
        }

    monkeypatch.setattr(bwd, "_http_request", fake_http)
    res = bwd.withdraw_usdt(50.0, "TAddr123456789012345678901234567890", "TRC20", dry_run=False)
    assert res["success"] is False
    assert res["binance_code"] == -4022
    assert "whitelist" in (res.get("binance_msg") or "").lower()
    assert res["http_status"] == 400


def test_preflight_zero_spot_balance(binance_env, monkeypatch):
    bwd = binance_env["bwd"]

    def fake_spot(**kwargs):
        return {"success": True, "free": 0.0, "mode": "live"}

    def fake_capital(**kwargs):
        return {
            "success": True,
            "body": [{
                "coin": "USDT",
                "networkList": [{"network": "TRX", "withdrawFee": "1.5"}],
            }],
        }

    def fake_whitelist(coin="USDT", **kwargs):
        return {
            "success": True,
            "addresses": [{
                "address": "TBinanceUSDTaddr1234567890",
                "network": "TRX",
            }],
        }

    monkeypatch.setattr(bwd, "get_spot_usdt_free", fake_spot)
    monkeypatch.setattr(bwd, "get_capital_config", fake_capital)
    monkeypatch.setattr(bwd, "get_withdraw_address_list", fake_whitelist)

    pf = bwd.preflight_withdraw_usdt(
        150.0, "TBinanceUSDTaddr1234567890", "TRC20", sales_pool_usdt=1445.0,
    )
    assert pf["ready"] is False
    codes = [b["code"] for b in pf["blockers"]]
    assert "insufficient_spot_balance" in codes
    spot_blocker = next(b for b in pf["blockers"] if b["code"] == "insufficient_spot_balance")
    assert "sales pool" in spot_blocker["message"].lower()
    assert spot_blocker["sales_pool_usdt"] == 1445.0


def test_preflight_missing_whitelist(binance_env, monkeypatch):
    bwd = binance_env["bwd"]

    monkeypatch.setattr(
        bwd, "get_spot_usdt_free",
        lambda **kwargs: {"success": True, "free": 2000.0},
    )
    monkeypatch.setattr(
        bwd, "get_capital_config",
        lambda **kwargs: {
            "success": True,
            "body": [{"coin": "USDT", "networkList": [{"network": "TRX", "withdrawFee": "1.5"}]}],
        },
    )
    monkeypatch.setattr(
        bwd, "get_withdraw_address_list",
        lambda coin="USDT", **kwargs: {"success": True, "addresses": [{"address": "TXLMonly", "network": "XLM"}]},
    )

    pf = bwd.preflight_withdraw_usdt(150.0, "TBinanceUSDTaddr1234567890", "TRC20")
    assert pf["ready"] is False
    assert any(b["code"] == "address_not_whitelisted" for b in pf["blockers"])


def test_preflight_success(binance_env, monkeypatch):
    bwd = binance_env["bwd"]
    addr = "TBinanceUSDTaddr1234567890"

    monkeypatch.setattr(
        bwd, "get_spot_usdt_free",
        lambda **kwargs: {"success": True, "free": 2000.0},
    )
    monkeypatch.setattr(
        bwd, "get_capital_config",
        lambda **kwargs: {
            "success": True,
            "body": [{"coin": "USDT", "networkList": [{"network": "TRX", "withdrawFee": "1.5"}]}],
        },
    )
    monkeypatch.setattr(
        bwd, "get_withdraw_address_list",
        lambda coin="USDT", **kwargs: {"success": True, "addresses": [{"address": addr, "network": "TRX"}]},
    )

    pf = bwd.preflight_withdraw_usdt(150.0, addr, "TRC20")
    assert pf["ready"] is True
    assert pf["blockers"] == []


def test_withdraw_binance_live_blocks_spot_insufficient(binance_env, monkeypatch):
    ex = binance_env["ex"]
    pay = binance_env["pay"]
    pool = binance_env["pool"]

    pool_uid = pool.sales_pool_user_id()
    ex._adjust_balance(pool_uid, "USDT", 1445.0)
    pay.configure_binance("", "", withdraw_address="TBinanceUSDTaddr1234567890", network="TRC20")

    monkeypatch.setenv("EXCHANGE_PAYOUT_BINANCE_LIVE", "1")
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    monkeypatch.setattr(pay, "binance_withdraw_live_enabled", lambda: True)
    monkeypatch.setattr(pay, "get_spot_usdt_free", lambda **kwargs: {"success": True, "free": 0.0})
    monkeypatch.setattr(
        pay, "preflight_withdraw_usdt",
        lambda *a, **k: {"ready": False, "blockers": [{"code": "insufficient_spot_balance"}]},
    )

    res = pay.withdraw_binance(150.0, min_amount=5.0)
    assert res["success"] is False
    assert res["error"] == "binance_spot_insufficient"
    wallet = ex.get_wallet(pool_uid)
    assert float(wallet["assets"]["USDT"]) == 1445.0
