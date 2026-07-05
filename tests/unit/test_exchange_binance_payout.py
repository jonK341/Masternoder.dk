"""Binance fiat bank wire payout — paper flow + fee estimate."""
import pytest


@pytest.fixture
def bank_wire_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_secrets_vault_service as vault
    from backend.services import exchange_payout_service as pay
    from backend.services import exchange_binance_payout_service as bw

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    wallets = data / "wallets"
    wallets.mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(wallets))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(vault, "_DATA_DIR", str(data))
    monkeypatch.setattr(vault, "_VAULT_PATH", str(data / "secrets_vault.enc"))
    monkeypatch.setattr(vault, "_REGISTRY_PATH", str(data / "wallet_registry.json"))
    monkeypatch.setattr(pay, "_PAYOUT_PATH", str(data / "payout_config.json"))
    monkeypatch.setattr(pay, "_SWEEPS_PATH", str(data / "payout_sweeps.jsonl"))
    monkeypatch.setattr(bw, "_PAYOUT_PATH", str(data / "payout_config.json"))
    monkeypatch.setattr(bw, "_SWEEPS_PATH", str(data / "payout_sweeps.jsonl"))
    monkeypatch.delenv("EXCHANGE_PAYOUT_BINANCE_LIVE", raising=False)
    monkeypatch.delenv("EXCHANGE_ARBITRAGE_LIVE", raising=False)
    return {"ex": ex, "vault": vault, "pay": pay, "bw": bw}


def test_estimate_bank_wire_fee_defaults(bank_wire_env):
    bw = bank_wire_env["bw"]
    fee = bw.estimate_bank_wire_fee()
    assert fee["success"] is True
    assert fee["currency"] == "EUR"
    assert fee["fee"] == 2.0
    assert fee["source"] == "config"


def test_get_withdraw_methods_paper(bank_wire_env):
    bw = bank_wire_env["bw"]
    res = bw.get_withdraw_methods()
    assert res["success"] is True
    assert len(res["methods"]) >= 1
    assert res["methods"][0]["payment_method"] == "bank_transfer"
    assert res["live_enabled"] is False


def test_configure_and_paper_withdraw(bank_wire_env, monkeypatch):
    pytest.importorskip("cryptography")
    pay = bank_wire_env["pay"]
    bw = bank_wire_env["bw"]
    ex = bank_wire_env["ex"]

    monkeypatch.setenv("EXCHANGE_VAULT_KEY", "bank-wire-test-key")
    pay.configure_binance("APIKEY", "SECRET", deposit_addresses={"USDT": "Taddr"})
    cfg_res = bw.configure_bank_beneficiary("DK1234567890123456", currency="EUR")
    assert cfg_res["success"] is True
    assert "3456" in cfg_res["account_number_masked"]

    res = bw.initiate_bank_withdraw(75.0, currency="EUR")
    assert res["success"] is True
    assert res["live"] is False
    assert res["withdrawn"]["mode"] == "paper"
    assert res["withdrawn"]["method"] == "binance_bank_wire"
    assert res["withdrawn"]["destination"] == "binance_bank_wire"

    sweeps_path = str(bank_wire_env["pay"]._SWEEPS_PATH)
    with open(sweeps_path, encoding="utf-8") as fh:
        lines = [ln for ln in fh if ln.strip()]
    assert len(lines) == 1
    import json
    row = json.loads(lines[0])
    assert row["method"] == "binance_bank_wire"
    assert row["amount"] == 75.0


def test_plan_bank_wire_below_min(bank_wire_env, monkeypatch):
    bw = bank_wire_env["bw"]
    bw.configure_bank_beneficiary("DK9999999999999999")
    plan = bw.plan_bank_wire_sweep()
    assert plan.get("actionable") is False
    assert plan.get("reason") in ("below_min_withdraw", "below_min_sweep")
