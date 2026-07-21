"""Venue funding rotation — sell-to-fund, leg prefund, agent round-robin."""
import json

import pytest


@pytest.fixture
def venue_rotation_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import venue_funding_rotation_service as vfr

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    cfg_path = data / "profit_path_protocol.json"
    ledger_path = data / "profit_path_ledger.jsonl"

    monkeypatch.setattr(ppp, "_CFG_PATH", str(cfg_path))
    monkeypatch.setattr(ppp, "_LEDGER_PATH", str(ledger_path))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(vfr, "_STATE_PATH", str(data / "agent_trade_rotation_state.json"))

    (data / "profit_path_protocol.json").write_text(
        json.dumps({"enabled": True, "rotation_live_enabled": False, "agent_rotation_enabled": True}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        vfr,
        "rotation_agent_ids",
        lambda: ["agent_a", "agent_b"],
    )
    monkeypatch.setattr(
        vfr,
        "_venue_rotation_eligible",
        lambda vid: str(vid or "").lower() in ("binance", "nonkyc"),
    )

    return {"vfr": vfr, "data": data}


def test_sell_coins_to_fund_venue_dry_run(venue_rotation_env, monkeypatch):
    vfr = venue_rotation_env["vfr"]

    action = {
        "type": "external_market_sell",
        "venue_id": "nonkyc",
        "symbol": "DOGE",
        "side": "sell",
        "amount_usd": 50.0,
        "label": "Sell DOGE on nonkyc for USDT ~$50",
    }

    monkeypatch.setattr(vfr, "_quote_shortfall_action", lambda *a, **k: action)
    monkeypatch.setattr(
        vfr,
        "execute_rotation",
        lambda act, dry_run=True: {"success": True, "dry_run": dry_run, "mode": "paper"},
    )

    out = vfr.sell_coins_to_fund_venue("nonkyc", "USDT", 50.0, dry_run=True)
    assert out["success"] is True
    assert out["venue_id"] == "nonkyc"
    assert out["target_asset"] == "USDT"


def test_sell_coins_to_fund_venue_no_inventory(venue_rotation_env, monkeypatch):
    vfr = venue_rotation_env["vfr"]
    monkeypatch.setattr(vfr, "_quote_shortfall_action", lambda *a, **k: None)

    out = vfr.sell_coins_to_fund_venue("nonkyc", "USDT", 50.0)
    assert out["success"] is False
    assert out["error"] == "no_sellable_inventory"


def test_fund_venue_legs_already_funded(venue_rotation_env, monkeypatch):
    vfr = venue_rotation_env["vfr"]
    monkeypatch.setattr(
        vfr,
        "analyze_funding_gaps",
        lambda aid, sym, notion: {"funded_ok": True, "symbol": sym, "agent_id": aid},
    )

    out = vfr.fund_venue_legs_for_symbol("agent_a", "DOGE", 25.0)
    assert out["success"] is True
    assert out["already_funded"] is True


def test_restore_post_trade_inventory_dry_run(venue_rotation_env, monkeypatch):
    vfr = venue_rotation_env["vfr"]

    def fake_market_order(venue, side, sym, usd, **kwargs):
        return {"ok": True, "quantity": 100.0, "market": f"{sym}_USDT", "quote": "USDT"}

    monkeypatch.setattr(
        "backend.services.venue_funding_rotation_service.vapi.market_order_for_leg",
        fake_market_order,
    )
    monkeypatch.setattr(
        vfr,
        "execute_rotation",
        lambda act, dry_run=True: {"success": True, "dry_run": dry_run},
    )
    monkeypatch.setattr(
        "backend.services.venue_funding_rotation_service.ex._price_usd",
        lambda sym: 0.1 if sym == "DOGE" else 50000.0,
    )

    out = vfr.restore_post_trade_inventory(
        symbol="DOGE",
        buy_venue="binance",
        sell_venue="nonkyc",
        notional_usd=25.0,
        dry_run=True,
    )
    assert out["success"] is True
    assert len(out["legs"]) == 2


def test_rotation_status(venue_rotation_env):
    vfr = venue_rotation_env["vfr"]
    status = vfr.rotation_status()
    assert status["success"] is True
    assert status["current_agent_id"] == "agent_a"
    assert status["agent_ids"] == ["agent_a", "agent_b"]


def test_run_agent_trade_rotation_cycle_advances_on_execute(venue_rotation_env, monkeypatch):
    vfr = venue_rotation_env["vfr"]

    tick_calls = []

    def fake_tick(*, active_agent_id=None, hot_symbols=None, **kwargs):
        tick_calls.append(active_agent_id)
        return {
            "success": True,
            "executed_count": 1,
            "actions": [{
                "agent_id": active_agent_id,
                "executed": True,
                "best": {
                    "symbol": "DOGE",
                    "buy_venue": "binance",
                    "sell_venue": "nonkyc",
                    "notional_usd": 25.0,
                    "buy_ask": 0.1,
                },
            }],
        }

    monkeypatch.setattr(
        "backend.services.exchange_arbitrage_service.run_paper_tick",
        fake_tick,
    )
    monkeypatch.setattr(
        vfr,
        "restore_post_trade_inventory",
        lambda **kw: {"success": True, "legs": []},
    )
    monkeypatch.setattr(vfr, "rotation_live_enabled", lambda: False)

    out = vfr.run_agent_trade_rotation_cycle(force=True)
    assert out["success"] is True
    assert out["executed"] is True
    assert out["agent_id"] == "agent_a"
    assert out["next_agent_id"] == "agent_b"
    assert tick_calls == ["agent_a"]

    status = vfr.rotation_status()
    assert status["current_agent_id"] == "agent_b"


def test_run_paper_tick_active_agent_filter(monkeypatch):
    from backend.services import exchange_arbitrage_service as arb

    cfg = {
        "enabled": True,
        "paper_trade_usd": 25,
        "supported_symbols": ["BTC"],
        "venues": [{"id": "binance", "enabled": True}, {"id": "nonkyc", "enabled": True}],
        "arbitrage_agents": [
            {"id": "agent_x", "symbols": ["BTC"], "venues": ["binance", "nonkyc"]},
            {"id": "agent_y", "symbols": ["BTC"], "venues": ["binance", "nonkyc"]},
        ],
    }

    monkeypatch.setattr(arb.conn, "load_connectors_config", lambda: cfg)
    monkeypatch.setattr(arb, "live_enabled", lambda: False)
    monkeypatch.setattr(arb.conn, "fetch_prices", lambda **kw: {"prices": {}, "source": "test"})
    monkeypatch.setattr(arb, "_live_api_ready_venues", lambda v: v)
    monkeypatch.setattr(arb, "effective_min_margin_bps", lambda c: 30)
    monkeypatch.setattr(arb, "_effective_transfer_cost_bps", lambda c: 5)
    monkeypatch.setattr(arb, "read_account", lambda aid: {"agent_id": aid, "ticks": 0})
    monkeypatch.setattr(arb, "write_account", lambda acct: None)
    monkeypatch.setattr(
        arb,
        "scan_opportunities",
        lambda **kw: {"opportunities": []},
    )

    recorded = []

    def fake_record_scan(**kw):
        recorded.append(kw.get("agent_id"))
        return "path1"

    monkeypatch.setattr("backend.services.exchange_profit_path_service.record_scan", fake_record_scan)
    monkeypatch.setattr("backend.services.exchange_profit_path_service.record_execution", lambda **kw: None)

    out = arb.run_paper_tick(active_agent_id="agent_y")
    assert out["agent_count"] == 1
    assert recorded == ["agent_y"]
