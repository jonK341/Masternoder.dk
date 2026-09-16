"""Fiat converter — pool valuation, conversion plan, and paper execution."""
import pytest


PRICES = {"BTC": 60000.0, "ETH": 3000.0, "USDC": 1.0, "USDT": 1.0, "ADA": 0.5, "XYZ": 0.0}


@pytest.fixture
def env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_fiat_converter_service as fc
    from backend.services import exchange_payout_service as pay
    from backend.services import exchange_sales_pool_service as pool

    data = tmp_path / "crypto_exchange"
    wallets = data / "wallets"
    wallets.mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(wallets))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(ex, "_price_usd", lambda sym, cfg=None: PRICES.get(str(sym).upper(), 0.0))
    monkeypatch.setattr(fc, "_CONV_LEDGER_PATH", str(data / "fiat_conversions.jsonl"))
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

    for flag in ("EXCHANGE_FIAT_CONVERT_LIVE", "EXCHANGE_ARBITRAGE_LIVE",
                 "EXCHANGE_PAYOUT_PAYPAL_LIVE", "EXCHANGE_PAYOUT_PAYPAL_EMAIL",
                 "EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT"):
        monkeypatch.delenv(flag, raising=False)

    pool_uid = pool.sales_pool_user_id()
    ex._adjust_balance(pool_uid, "BTC", 0.1)     # $6000
    ex._adjust_balance(pool_uid, "ETH", 2.0)     # $6000
    ex._adjust_balance(pool_uid, "USDC", 1000.0)  # $1000 stable
    ex._adjust_balance(pool_uid, "XYZ", 5.0)     # unpriced

    return {"ex": ex, "fc": fc, "pay": pay, "pool": pool, "pool_uid": pool_uid}


def test_pool_valuation(env):
    fc = env["fc"]
    val = fc.pool_valuation()
    assert val["success"] is True
    assert val["total_usd"] == pytest.approx(13000.0)
    assert val["stable_usd"] == pytest.approx(1000.0)
    assert val["crypto_usd"] == pytest.approx(12000.0)
    xyz = next(r for r in val["assets"] if r["symbol"] == "XYZ")
    assert xyz["priced"] is False


def test_plan_target_stable(env):
    fc = env["fc"]
    plan = fc.plan_fiat_conversion(venue="binance", target="USDC")
    assert plan["success"] is True
    assert plan["target_kind"] == "stable"
    assert plan["consolidation_stable"] == "USDC"
    syms = {leg["symbol"] for leg in plan["sell_legs"]}
    assert syms == {"BTC", "ETH"}
    assert plan["stable_on_hand_usd"] == pytest.approx(1000.0)
    # binance fee 10 bps -> 0.1%
    assert plan["est_fees_usd"] == pytest.approx(12.0)
    assert plan["est_total_stable_usd"] == pytest.approx(12988.0)
    assert any(s["reason"] == "no_price" for s in plan["skipped"])
    assert plan["actionable"] is True


def test_execute_paper_consolidates_to_stable(env):
    fc, ex, pool_uid = env["fc"], env["ex"], env["pool_uid"]
    res = fc.execute_fiat_conversion(venue="binance", target="USDC", dry_run=True)
    assert res["success"] is True
    assert res["mode"] == "paper"
    assert len(res["sells"]) == 2
    assets = ex.get_wallet(pool_uid)["assets"]
    assert float(assets.get("BTC") or 0) == pytest.approx(0.0)
    assert float(assets.get("ETH") or 0) == pytest.approx(0.0)
    assert float(assets["USDC"]) == pytest.approx(12988.0)


def test_plan_fiat_offramp_no_email(env):
    fc = env["fc"]
    plan = fc.plan_fiat_conversion(venue="binance", target="USD")
    assert plan["target_kind"] == "fiat"
    assert plan["offramp"]["rail"] == "manual"


def test_execute_fiat_offramp_paper_with_paypal(env):
    fc, ex, pay, pool_uid = env["fc"], env["ex"], env["pay"], env["pool_uid"]
    pay.configure_paypal("owner@example.com")
    res = fc.execute_fiat_conversion(venue="binance", target="USD", dry_run=True)
    assert res["success"] is True
    assert res["offramp"]["success"] is True
    assert res["offramp"]["rail"] == "paypal"
    assert res["offramp"]["mode"] == "paper"
    assert res["offramp"]["amount_usd"] == pytest.approx(12988.0)
    # Stable off-ramped out of the pool ledger.
    assert float(ex.get_wallet(pool_uid)["assets"].get("USDC") or 0) == pytest.approx(0.0)


def test_conversion_history_records(env):
    fc = env["fc"]
    fc.execute_fiat_conversion(venue="binance", target="USDC", dry_run=True)
    hist = fc.conversion_history()
    assert hist["success"] is True
    assert hist["count"] >= 2
    assert all(r["phase"] == "sell" for r in hist["conversions"])


def test_status_snapshot(env):
    fc = env["fc"]
    st = fc.fiat_converter_status()
    assert st["success"] is True
    assert st["valuation"]["total_usd"] == pytest.approx(13000.0)
    assert st["default_plan"]["target"] == "USD"
