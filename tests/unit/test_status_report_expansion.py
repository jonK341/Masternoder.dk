"""Status report expansion tests — reserves overview, explorer env, treasury mode, claim profit."""
import json
import pytest


def test_explorer_env_overrides(monkeypatch):
    monkeypatch.setenv("MN2_EXPLORER_BASE_URL", "https://explorer.example/")
    monkeypatch.setenv("MN2_EXPLORER_KIND", "iquidus")
    from backend.services.mn2_explorer_urls import explorer_address_url, load_explorer_config

    cfg = load_explorer_config()
    assert cfg["explorer_base_url"] == "https://explorer.example/"
    assert explorer_address_url("MxTest", cfg) == "https://explorer.example/address/MxTest"


def test_treasury_status_mode_filter(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_treasury_service as tre

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    ledger = data / "treasury_stash.jsonl"
    ledger.write_text(
        json.dumps({"amount_usd": 10, "mode": "paper"}) + "\n"
        + json.dumps({"amount_usd": 5, "mode": "live"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(tre, "_LEDGER_PATH", str(ledger))
    monkeypatch.setattr(tre, "_CFG_PATH", str(tmp_path / "exchange_treasury_config.json"))
    (tmp_path / "exchange_treasury_config.json").write_text('{"treasury_user_id":"platform_treasury"}', encoding="utf-8")

    live = tre.treasury_status(mode="live")
    assert live["ledger_stashed_usd"] == 5.0
    assert live["ledger_entries"] == 1


def test_reserves_overview_structure(monkeypatch):
    from backend.services.mn2_proof_of_reserves_service import reserves_overview

    monkeypatch.setattr(
        "backend.services.mn2_proof_of_reserves_service.proof_of_reserves",
        lambda force=False: {"success": True, "coverage_ratio": 1.0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_proof_of_reserves_service.yield_report",
        lambda force=False: {"success": True, "lifetime": {}},
    )
    monkeypatch.setattr(
        "backend.services.exchange_treasury_service.treasury_status",
        lambda mode=None: {"success": True, "mn2_balance": 100},
    )
    out = reserves_overview()
    assert out["success"] is True
    assert "proof_of_reserves" in out
    assert "exchange_treasury" in out
    assert "fee_treasury" in out


def test_claim_profit_credits_mn2(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import agent_marketplace_service as mkt

    data = tmp_path / "crypto_exchange"
    (data / "user_agents").mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(mkt, "_USER_AGENTS_DIR", str(data / "user_agents"))
    monkeypatch.setattr(mkt, "_SALES_PATH", str(data / "agent_sales.jsonl"))
    monkeypatch.setattr(ex, "_mn2_usd", lambda: 0.05)

    uid = "test_user_claim"
    mkt._write_user_agents(uid, {
        "agents": {
            "ua_test1": {
                "agent_id": "ua_test1",
                "realized_profit_usd": 5.0,
                "enabled": True,
            }
        }
    })
    credits = []

    def fake_adjust(user_id, quote, delta, source, meta):
        credits.append((user_id, delta))

    monkeypatch.setattr(ex, "_adjust_quote_balance", fake_adjust)

    r = mkt.claim_profit(uid)
    assert r["success"] is True
    assert r["claimed_usd"] == 5.0
    assert credits and credits[0][1] == 100.0
