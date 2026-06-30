"""Owner business control board: profit aggregation + bot/supervisor controls."""
import pytest


@pytest.fixture
def ctl_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import trading_bots_control_service as ctl

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    (data / "wallets").mkdir(parents=True)

    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(ex, "_TRADES_PATH", str(data / "trades.jsonl"))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(data / "wallets"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(ctl, "_CONTROL_PATH", str(data / "trading_bots_control.json"))

    # Seed one arbitrage bot account with realized profit.
    arb.write_account({
        "agent_id": "arb_agent_btc_eth", "realized_profit_usd": 42.5,
        "trade_count": 3, "notional_traded_usd": 1500.0, "by_venue": {},
        "wallet_label": "arb_btc_eth_wallet", "last_action": None,
    })
    return {"ex": ex, "arb": arb, "ctl": ctl}


def test_overview_aggregates_bot_profits(ctl_env):
    ctl = ctl_env["ctl"]
    ov = ctl.business_overview()
    assert ov["success"] is True
    bot = next(b for b in ov["bots"] if b["id"] == "arb_agent_btc_eth")
    assert bot["realized_pnl_usd"] == 42.5
    assert bot["total_pnl_usd"] == 42.5
    assert ov["totals"]["total_profit_usd"] >= 42.5
    sup = next(s for s in ov["supervisors"] if s["id"] == "sup_arbitrage")
    assert sup["profit_usd"] >= 42.5
    assert "arb_agent_btc_eth" in sup["bot_ids"]
    # Five supervisor agents control the business.
    assert len(ov["supervisors"]) == 5


def test_set_bot_enabled_override(ctl_env):
    ctl = ctl_env["ctl"]
    assert ctl.set_bot_enabled("arb_agent_btc_eth", False)["success"] is True
    bots = ctl.list_bots()
    bot = next(b for b in bots if b["id"] == "arb_agent_btc_eth")
    assert bot["enabled"] is False


def test_supervisor_pause_disables_its_bots(ctl_env):
    ctl = ctl_env["ctl"]
    assert ctl.set_supervisor_enabled("sup_arbitrage", False)["success"] is True
    bot = next(b for b in ctl.list_bots() if b["id"] == "arb_agent_btc_eth")
    assert bot["enabled"] is False


def test_kill_switch_blocks_run_and_disables_all(ctl_env):
    ctl = ctl_env["ctl"]
    assert ctl.set_kill_switch(True)["success"] is True
    ov = ctl.business_overview()
    assert ov["kill_switch"] is True
    assert all(b["enabled"] is False for b in ov["bots"])
    run = ctl.run_all_bots()
    assert run["success"] is False
    assert run["error"] == "kill_switch_active"


def test_run_all_reports_supervisor_paused(ctl_env):
    ctl = ctl_env["ctl"]
    ctl.set_supervisor_enabled("sup_arbitrage", False)
    ctl.set_supervisor_enabled("sup_crosstrade", False)
    run = ctl.run_all_bots()
    assert run["success"] is True
    assert run["results"]["arbitrage"]["error"] == "supervisor_paused"
    assert run["results"]["cross_trade"]["error"] == "supervisor_paused"
