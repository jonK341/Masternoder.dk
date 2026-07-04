"""Profit Path Protocol — record, search, summary tests."""
import pytest


@pytest.fixture
def ppp_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_path_service as ppp

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)

    cfg_path = data / "profit_path_protocol.json"
    ledger_path = data / "profit_path_ledger.jsonl"

    monkeypatch.setattr(ppp, "_CFG_PATH", str(cfg_path))
    monkeypatch.setattr(ppp, "_LEDGER_PATH", str(ledger_path))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))

    return {"ppp": ppp, "ledger_path": ledger_path}


def test_record_scan_and_search(ppp_env):
    ppp = ppp_env["ppp"]
    opp = {
        "symbol": "BTC",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "gross_bps": 50.0,
        "fee_bps": 25.0,
        "net_bps": 25.0,
        "notional_usd": 200.0,
    }
    pid = ppp.record_scan(
        agent_id="arb_test",
        strategy="spatial_arb",
        best=opp,
        threshold_bps=30,
        mode="paper",
        decision="skip",
        skip_reason="below_threshold",
    )
    assert len(pid) == 8

    res = ppp.search_paths(agent_id="arb_test", hours=24, limit=10)
    assert res["success"] is True
    assert res["count"] == 1
    row = res["paths"][0]
    assert row["path_id"] == pid
    assert row["phase"] == "scan"
    assert row["symbol"] == "BTC"
    assert row["venues"]["buy"] == "binance"
    assert row["decision"] == "skip"
    assert row["skip_reason"] == "below_threshold"


def test_record_execution_and_summary(ppp_env):
    ppp = ppp_env["ppp"]
    opp = {
        "symbol": "ETH",
        "buy_venue": "coinbase",
        "sell_venue": "bingx",
        "gross_bps": 80.0,
        "fee_bps": 20.0,
        "net_bps": 60.0,
        "notional_usd": 150.0,
    }
    pid = ppp.record_scan(
        agent_id="arb_exec",
        best=opp,
        decision="attempt",
        mode="paper",
    )
    ppp.record_execution(
        path_id=pid,
        agent_id="arb_exec",
        opp=opp,
        exec_res={"success": True, "mode": "paper", "est_profit_usd": 0.45, "notional_usd": 150},
    )

    summary = ppp.profit_path_summary(hours=24)
    assert summary["success"] is True
    assert summary["scan_count"] >= 1
    assert summary["attempt_count"] >= 1
    assert summary["fill_count"] >= 1
    assert summary["avg_net_bps"] > 0


def test_search_filters_min_net_bps_and_decision(ppp_env):
    ppp = ppp_env["ppp"]
    low = {"symbol": "DOGE", "buy_venue": "a", "sell_venue": "b", "net_bps": 5.0, "fee_bps": 10, "gross_bps": 15}
    high = {"symbol": "DOGE", "buy_venue": "c", "sell_venue": "d", "net_bps": 55.0, "fee_bps": 10, "gross_bps": 65}
    ppp.record_scan(agent_id="f1", best=low, decision="skip", skip_reason="below_threshold")
    ppp.record_scan(agent_id="f2", best=high, decision="skip", skip_reason="below_threshold")

    hits = ppp.search_paths(min_net_bps=40, hours=24)
    assert hits["count"] == 1
    assert hits["paths"][0]["net_bps"] == 55.0

    skips = ppp.search_paths(decision="skip", hours=24)
    assert skips["count"] == 2


def test_suggest_improvements_funding_hint(ppp_env):
    ppp = ppp_env["ppp"]
    opp = {
        "symbol": "XRP",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "net_bps": 40.0,
        "fee_bps": 15,
        "gross_bps": 55,
        "notional_usd": 250,
    }
    for _ in range(3):
        ppp.record_scan(
            agent_id="arb_fund",
            best=opp,
            decision="skip",
            skip_reason="insufficient_venue_balance",
            notional_usd=250,
        )

    hints = ppp.suggest_improvements(hours=24)
    assert hints["success"] is True
    assert hints["suggestion_count"] >= 1
    messages = " ".join(s["message"] for s in hints["suggestions"])
    assert "balance" in messages.lower() or "fund" in messages.lower()


def test_export_rows(ppp_env):
    ppp = ppp_env["ppp"]
    ppp.record_scan(agent_id="exp", decision="skip", skip_reason="no_profitable_spread")
    out = ppp.export_rows(limit=10)
    assert out["success"] is True
    assert out["count"] >= 1
