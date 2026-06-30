"""PayPal profit payout tests."""
import os
import pytest


@pytest.fixture
def payout_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_payout_service as pay

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(pay, "_PAYOUT_PATH", str(data / "payout_config.json"))
    monkeypatch.setattr(pay, "_SWEEPS_PATH", str(data / "payout_sweeps.jsonl"))
    monkeypatch.setenv("EXCHANGE_PAYOUT_PAYPAL_EMAIL", "owner@test.com")
    monkeypatch.setenv("EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT", "50")
    monkeypatch.delenv("EXCHANGE_PAYOUT_PAYPAL_LIVE", raising=False)
    monkeypatch.setattr(pay, "_realized_total_usd", lambda: 100.0)
    monkeypatch.setattr(pay, "_treasury_stashed_usd", lambda: 80.0)
    return pay


def test_configure_paypal(payout_env):
    pay = payout_env
    r = pay.configure_paypal("owner@test.com", share_pct=0.25)
    assert r["success"] is True
    st = pay.payout_status()
    assert st["paypal"]["email"] == "owner@test.com"
    assert st["destination"] == "paypal"


def test_plan_paypal_sweep(payout_env):
    pay = payout_env
    pay.configure_paypal("owner@test.com", share_pct=0.5)
    plan = pay.plan_sweep(min_sweep_usd=5.0)
    assert plan["actionable"] is True
    assert plan["destination"] == "paypal"
    assert plan["receiver_email"] == "owner@test.com"
    assert plan["amount_usd"] == 50.0
    assert plan["mode"] == "paper"


def test_execute_paper_sweep(payout_env, monkeypatch):
    pay = payout_env
    monkeypatch.delenv("EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT", raising=False)
    pay.configure_paypal("owner@test.com", share_pct=1.0)
    out = pay.execute_sweep(min_sweep_usd=1.0)
    assert out["success"] is True
    assert out["swept"]["destination"] == "paypal"
    assert out["swept"]["mode"] == "paper"
    assert out["live"] is False
    st = pay.payout_status()
    assert st["swept_total_usd"] == 100.0
