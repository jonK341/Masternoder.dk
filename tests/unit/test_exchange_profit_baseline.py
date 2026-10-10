"""Profit trade baseline service tests."""
import json

import pytest


@pytest.fixture
def baseline_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_baseline_service as bl
    from backend.services import exchange_profit_path_service as ppp

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ppp, "_CFG_PATH", str(data / "profit_path_protocol.json"))
    monkeypatch.setattr(ppp, "_LEDGER_PATH", str(data / "profit_path_ledger.jsonl"))
    monkeypatch.setattr(bl, "_BASELINE_PATH", str(data / "profit_trade_baselines.jsonl"))
    (data / "profit_path_protocol.json").write_text(json.dumps({"enabled": True}), encoding="utf-8")
    return {"bl": bl, "data": data}


def test_record_and_list_baselines(baseline_env, monkeypatch):
    bl = baseline_env["bl"]
    monkeypatch.setattr(
        "backend.services.exchange_profit_agent_skills_service.on_baseline_trade_event",
        lambda row: {"success": True},
    )

    bid = bl.record_baseline_trade(
        predicted={"action_label": "Buy USDT on nonkyc ~$98", "amount_usd": 98, "expected_unlock_bps": 25},
        executed={"success": True, "mode": "live", "fill_usd": 98, "order_id": "o1"},
        source="rotation",
        route={"agent_id": "arb_live_dual_farm", "symbol": "USDT", "buy_venue": "nonkyc"},
        net_bps_at_exec=22.5,
    )
    assert len(bid) == 8

    listed = bl.list_baselines(hours=24, limit=10)
    assert listed["success"] is True
    assert listed["count"] == 1
    assert listed["baselines"][0]["baseline_id"] == bid
    assert listed["baselines"][0]["source"] == "rotation"

    summary = bl.baseline_summary(hours=24)
    assert summary["total"] == 1
    assert summary["success_count"] == 1
    assert summary["success_rate_pct"] == 100.0
    assert "rotation" in summary["by_source"]


def test_record_arb_baseline(baseline_env, monkeypatch):
    bl = baseline_env["bl"]
    monkeypatch.setattr(
        "backend.services.exchange_profit_agent_skills_service.on_baseline_trade_event",
        lambda row: {"success": True},
    )
    opp = {"symbol": "DOGE", "buy_venue": "binance", "sell_venue": "nonkyc", "notional_usd": 75, "net_bps": 21}
    exec_res = {
        "success": True,
        "mode": "live",
        "notional_usd": 75,
        "est_profit_usd": 0.15,
        "buy_order": {"order_id": "b1"},
        "sell_order": {"order_id": "s1"},
    }
    bid = bl.record_arb_baseline(opp, exec_res, source="fast_ext", agent_id="arb_live_dual_farm")
    assert bid
    rows = bl.list_baselines(source="fast_ext", limit=5)
    assert rows["count"] == 1


def test_list_baselines_filter_source(baseline_env, monkeypatch):
    bl = baseline_env["bl"]
    monkeypatch.setattr(
        "backend.services.exchange_profit_agent_skills_service.on_baseline_trade_event",
        lambda row: {"success": True},
    )
    bl.record_baseline_trade(
        predicted={"action_label": "a", "amount_usd": 10},
        executed={"success": False, "mode": "paper"},
        source="rotation",
    )
    bl.record_baseline_trade(
        predicted={"action_label": "b", "amount_usd": 20},
        executed={"success": True, "mode": "live"},
        source="arb",
    )
    rot = bl.list_baselines(source="rotation", limit=10)
    assert rot["count"] == 1
    assert rot["baselines"][0]["source"] == "rotation"
