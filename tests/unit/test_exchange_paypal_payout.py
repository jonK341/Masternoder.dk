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
    monkeypatch.delenv("EXCHANGE_AUTO_PAYPAL_SWEEP", raising=False)
    monkeypatch.setattr(pay, "_treasury_stashed_usd_by_mode", lambda mode: 100.0)
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
    assert st["sweep_ledger_mode"] == "paper"
    assert st["sweep_pool_usd"] == 100.0


def test_sweep_pool_uses_live_ledger_when_live(payout_env, monkeypatch):
    pay = payout_env
    monkeypatch.setenv("EXCHANGE_PAYOUT_PAYPAL_LIVE", "1")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test-client")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(pay, "_paypal_live_enabled", lambda: True)
    monkeypatch.setattr(
        pay,
        "_treasury_stashed_usd_by_mode",
        lambda mode: 12.0 if mode == "live" else 999999.0,
    )
    pay.configure_paypal("owner@test.com", share_pct=1.0)
    st = pay.payout_status()
    assert st["sweep_ledger_mode"] == "live"
    assert st["sweep_pool_usd"] == 12.0
    assert st["net_unswept_usd"] == 12.0


def test_live_gate_selects_live_path(payout_env, monkeypatch):
    pay = payout_env
    monkeypatch.setenv("EXCHANGE_PAYOUT_PAYPAL_LIVE", "1")
    monkeypatch.setenv("EXCHANGE_AUTO_PAYPAL_SWEEP", "1")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test-client")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(pay, "_paypal_live_enabled", lambda: True)
    monkeypatch.setattr(pay, "_treasury_stashed_usd_by_mode", lambda mode: 200.0 if mode == "live" else 0.0)

    def fake_payout(email, amount, note=""):
        return {"success": True, "payout_batch_id": "BATCH-TEST-1"}

    monkeypatch.setattr("backend.services.paypal_service.create_payout", fake_payout)
    pay.configure_paypal("owner@test.com", share_pct=1.0)
    plan = pay.plan_sweep(min_sweep_usd=5.0)
    assert plan["mode"] == "live"
    assert plan["actionable"] is True
    out = pay.execute_sweep(min_sweep_usd=5.0)
    assert out["success"] is True
    assert out["live"] is True
    assert out["swept"]["mode"] == "live"
    assert out["swept"]["payout_batch_id"] == "BATCH-TEST-1"


def test_without_live_env_stays_paper(payout_env, monkeypatch):
    pay = payout_env
    monkeypatch.delenv("EXCHANGE_PAYOUT_PAYPAL_LIVE", raising=False)
    monkeypatch.setattr(pay, "_treasury_stashed_usd_by_mode", lambda mode: 200.0 if mode == "live" else 100.0)
    pay.configure_paypal("owner@test.com", share_pct=1.0)
    plan = pay.plan_sweep(min_sweep_usd=5.0)
    assert plan["mode"] == "paper"
    assert plan["sweep_ledger_mode"] == "paper"
    out = pay.execute_sweep(min_sweep_usd=5.0)
    assert out["live"] is False
    assert out["swept"]["mode"] == "paper"
    assert out["swept"].get("payout_batch_id") is None
