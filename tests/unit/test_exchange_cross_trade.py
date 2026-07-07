"""Cross-venue auto-trader: search->execute gating, cooldown, loss cap, audit, live double-gate."""
import json
import pytest


@pytest.fixture
def ct(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_cross_trade_service as c

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(c, "_AUDIT_PATH", str(data / "cross_trade_audit.jsonl"))
    monkeypatch.setattr(c, "_STATE_PATH", str(data / "cross_trade_state.json"))
    cfg = tmp_path / "ct_cfg.json"
    cfg.write_text(json.dumps({
        "enabled": True, "venues": ["binance", "nonkyc", "xeggex"],
        "min_net_bps": 8.0, "notional_usd": 25.0, "cooldown_seconds": 3.0,
        "max_trades_per_run": 3, "daily_loss_cap_usd": 10.0,
    }), encoding="utf-8")
    monkeypatch.setattr(c, "_CFG_PATH", str(cfg))
    # default: no live flags
    monkeypatch.delenv("EXCHANGE_ARBITRAGE_LIVE", raising=False)
    monkeypatch.delenv("EXCHANGE_CROSS_TRADE_LIVE", raising=False)
    return c


def _stub_diffs(ct, monkeypatch, diffs):
    from backend.services import exchange_grid_bot_service as grid

    def fake_scan(**k):
        return {"success": True, "count": len(diffs), "differences": list(diffs)}
    monkeypatch.setattr(grid, "scan_cross_venue_differences", fake_scan)


def _stub_exec(ct, monkeypatch, *, profit=0.05, ok=True, mode="paper"):
    import backend.services.exchange_live_execution_service as lx
    calls = []

    def fake_exec(opp, *, agent_id, dry_run=None):
        calls.append({"opp": opp, "dry_run": dry_run})
        return {"success": ok, "mode": mode, "est_profit_usd": profit,
                "buy_order": {"order_id": "b1"}, "sell_order": {"order_id": "s1"}}
    monkeypatch.setattr(lx, "execute_spatial_arbitrage", fake_exec)
    return calls


def test_disabled_is_skipped(ct, monkeypatch):
    ct.save_config({"enabled": False})
    _stub_diffs(ct, monkeypatch, [{"symbol": "DOGE", "buy_venue": "xeggex", "sell_venue": "nonkyc",
                                   "buy_ask": 0.1, "sell_bid": 0.102, "net_bps": 30.0}])
    r = ct.run_once()
    assert r.get("skipped") and r.get("reason") == "disabled"


def test_executes_when_edge_clears_threshold(ct, monkeypatch):
    _stub_diffs(ct, monkeypatch, [
        {"symbol": "DOGE", "buy_venue": "xeggex", "sell_venue": "nonkyc",
         "buy_ask": 0.1, "sell_bid": 0.102, "net_bps": 30.0},
        {"symbol": "LINK", "buy_venue": "xeggex", "sell_venue": "nonkyc",
         "buy_ask": 7.8, "sell_bid": 7.83, "net_bps": 4.0},   # below 8 bps -> not fired
    ])
    calls = _stub_exec(ct, monkeypatch)
    r = ct.run_once(dry_run=True)
    fired = [e for e in r["executed"]]
    assert len(fired) == 1 and fired[0]["symbol"] == "DOGE"
    assert len(calls) == 1
    assert calls[0]["dry_run"] is True  # paper


def test_cooldown_blocks_repeat(ct, monkeypatch):
    _stub_diffs(ct, monkeypatch, [{"symbol": "DOGE", "buy_venue": "xeggex", "sell_venue": "nonkyc",
                                   "buy_ask": 0.1, "sell_bid": 0.102, "net_bps": 30.0}])
    _stub_exec(ct, monkeypatch)
    r1 = ct.run_once(dry_run=True)
    r2 = ct.run_once(dry_run=True)  # immediately again -> cooldown
    assert len(r1["executed"]) == 1
    assert len(r2["executed"]) == 0


def test_audit_trail_records(ct, monkeypatch):
    _stub_diffs(ct, monkeypatch, [{"symbol": "DOGE", "buy_venue": "xeggex", "sell_venue": "nonkyc",
                                   "buy_ask": 0.1, "sell_bid": 0.102, "net_bps": 30.0}])
    _stub_exec(ct, monkeypatch, profit=0.09)
    ct.run_once(dry_run=True)
    hist = ct.history()
    ev = [e for e in hist["events"] if e.get("event") == "execute"]
    assert ev and ev[0]["symbol"] == "DOGE" and ev[0]["mode"] == "paper"
    assert ev[0]["buy_order_id"] == "b1" and ev[0]["sell_order_id"] == "s1"
    st = ct.status()
    assert st["executed_fills"] == 1
    assert st["realized_pnl_usd"] == pytest.approx(0.09)


def test_daily_loss_cap_halts(ct, monkeypatch):
    _stub_diffs(ct, monkeypatch, [{"symbol": "DOGE", "buy_venue": "xeggex", "sell_venue": "nonkyc",
                                   "buy_ask": 0.1, "sell_bid": 0.102, "net_bps": 30.0}])
    # A losing fill accrues realized loss; set cap low so the next pass halts.
    _stub_exec(ct, monkeypatch, profit=-6.0)
    ct.save_config({"daily_loss_cap_usd": 5.0, "cooldown_seconds": 0.0})
    ct.run_once(dry_run=True)               # books -6 loss
    r2 = ct.run_once(dry_run=True)          # over the 5 cap -> halt
    assert r2.get("halted") and r2.get("reason") == "daily_loss_cap"


def test_preview_marks_executable_when_both_legs_funded(ct, monkeypatch):
    _stub_diffs(ct, monkeypatch, [
        {"symbol": "DOGE", "buy_venue": "xeggex", "sell_venue": "nonkyc",
         "buy_ask": 0.1, "sell_bid": 0.102, "net_bps": 30.0, "route": "xeggex\u2192nonkyc"},
        {"symbol": "LINK", "buy_venue": "xeggex", "sell_venue": "nonkyc",
         "buy_ask": 7.8, "sell_bid": 7.9, "net_bps": 25.0, "route": "xeggex\u2192nonkyc"},
    ])
    import backend.services.exchange_venue_api_service as vapi

    def fake_funded(opp, **k):
        # DOGE fully funded on both legs; LINK missing the sell-side coin.
        if str(opp.get("symbol")) == "DOGE":
            return {"ok": True, "buy": {"ok": True, "free": 100, "need": 25},
                    "sell": {"ok": True, "free": 300, "need": 250}}
        return {"ok": False, "buy": {"ok": True, "free": 100, "need": 25},
                "sell": {"ok": False, "free": 0, "need": 3}}
    monkeypatch.setattr(vapi, "opportunity_funded", fake_funded)
    pv = ct.preview()
    assert pv["success"] and pv["count"] == 2 and pv["executable_now"] == 1
    doge = next(c for c in pv["candidates"] if c["symbol"] == "DOGE")
    link = next(c for c in pv["candidates"] if c["symbol"] == "LINK")
    assert doge["executable_now"] and doge["verdict"] == "executable_now_hedged"
    assert not link["executable_now"] and link["verdict"] == "needs_funding_or_transfer"


def test_hedged_fill_tracks_inventory_skew(ct, monkeypatch):
    _stub_diffs(ct, monkeypatch, [{"symbol": "DOGE", "buy_venue": "xeggex", "sell_venue": "nonkyc",
                                   "buy_ask": 0.10, "sell_bid": 0.102, "net_bps": 30.0}])
    import backend.services.exchange_live_execution_service as lx
    # return a quantity so skew can be tracked (notional 25 / 0.10 = 250)
    monkeypatch.setattr(lx, "execute_spatial_arbitrage",
                        lambda opp, *, agent_id, dry_run=None: {"success": True, "mode": "paper",
                        "est_profit_usd": 0.05, "quantity": 250.0,
                        "buy_order": {"order_id": "b"}, "sell_order": {"order_id": "s"}})
    ct.run_once(dry_run=True)
    rb = ct.rebalance_hint()["skew"]
    by = {(m["venue"], m["asset"]): m["net_base"] for m in rb}
    assert by[("xeggex", "DOGE")] == pytest.approx(250.0)   # buy venue accumulates coin
    assert by[("nonkyc", "DOGE")] == pytest.approx(-250.0)  # sell venue depletes coin


def test_live_gate_requires_both_flags(ct, monkeypatch):
    assert ct.cross_trade_live_enabled() is False
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    assert ct.cross_trade_live_enabled() is False   # still needs the cross-trade flag
    monkeypatch.setenv("EXCHANGE_CROSS_TRADE_LIVE", "1")
    assert ct.cross_trade_live_enabled() is True
