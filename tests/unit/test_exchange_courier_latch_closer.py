"""Unit tests for courier arm, latch sniper, and closer claw."""
from __future__ import annotations


def test_courier_imbalance_detects_poor_venue():
    from backend.services import exchange_courier_arm_service as courier

    imb = courier._imbalance(
        [
            {"venue": "binance", "quote": "USDC", "free": 1.0},
            {"venue": "nonkyc", "quote": "USDT", "free": 20.0},
        ],
        floor=12.0,
    )
    assert imb["skewed"] is True
    assert imb["poor"]["venue"] == "binance"
    assert imb["move_usd"] > 0


def test_courier_tick_raises_on_poor(monkeypatch, tmp_path):
    from backend.services import exchange_courier_arm_service as courier

    monkeypatch.setenv("COURIER_ARM_ENABLED", "1")
    monkeypatch.setattr(courier, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(courier, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(
        courier,
        "_quote_snaps",
        lambda: [
            {"venue": "binance", "quote": "USDC", "free": 1.0},
            {"venue": "nonkyc", "quote": "USDT", "free": 20.0},
        ],
    )
    monkeypatch.setattr(
        "backend.services.exchange_spread_hunter_arm_service._raise_quote_on_buy_venue",
        lambda *a, **k: {
            "success": True,
            "action": "prefund_sell",
            "venue": "binance",
            "symbol": "ADA",
            "sell_usd": 8.0,
        },
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_head_service.set_courier_hint",
        lambda hint: None,
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_head_service.get_prefund_hint",
        lambda: {"symbol": "ADA"},
    )
    # After raise, pretend still slightly skewed so hint path is exercised once.
    calls = {"n": 0}

    def snaps():
        calls["n"] += 1
        if calls["n"] <= 1:
            return [
                {"venue": "binance", "quote": "USDC", "free": 1.0},
                {"venue": "nonkyc", "quote": "USDT", "free": 20.0},
            ]
        return [
            {"venue": "binance", "quote": "USDC", "free": 9.0},
            {"venue": "nonkyc", "quote": "USDT", "free": 20.0},
        ]

    monkeypatch.setattr(courier, "_quote_snaps", snaps)
    out = courier.run_courier_tick(force=True)
    assert out["moved"] is True
    assert out["action"]["sell_usd"] == 8.0


def test_latch_arms_and_fires_when_skew_clears(monkeypatch, tmp_path):
    from backend.services import exchange_latch_sniper_service as latch

    monkeypatch.setenv("LATCH_SNIPER_ENABLED", "1")
    monkeypatch.setenv("LATCH_MIN_BPS", "12")
    monkeypatch.setattr(latch, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(latch, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(latch, "_candidate_from_hunter", lambda: None)
    latch.arm_latch(
        symbol="OP",
        buy_venue="nonkyc",
        sell_venue="binance",
        net_bps=80.0,
        mid_skew_bps=120.0,
        est_profit_usd=0.12,
        notional_usd=15.0,
        source="test",
    )
    monkeypatch.setattr(
        latch,
        "_recheck_latch",
        lambda row: {
            "ok": True,
            "mid_skew_bps": 20.0,
            "opportunity": {
                "symbol": "OP",
                "buy_venue": "nonkyc",
                "sell_venue": "binance",
                "net_bps": 40.0,
                "est_profit_usd": 0.06,
                "notional_usd": 15.0,
                "buy_ask": 1.0,
                "sell_bid": 1.01,
                "profitable": True,
            },
        },
    )
    monkeypatch.setattr(
        latch.arb,
        "prepare_live_opportunity",
        lambda o, **kw: {"ok": True, "opportunity": dict(o)},
    )
    monkeypatch.setattr(latch.arb, "live_enabled", lambda: False)
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.execute_spatial_arbitrage",
        lambda *a, **k: {"success": True, "mode": "paper", "quantity": 1, "notional_usd": 15},
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.book_agent_profit",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_scan",
        lambda **kw: "path-latch",
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_execution",
        lambda **kw: None,
    )
    monkeypatch.setattr(
        "backend.services.exchange_closer_claw_service.note_execution_legs",
        lambda *a, **k: None,
    )
    out = latch.run_latch_tick(force=True)
    assert out["fired"] is True
    assert out["pending"] == 0
    assert out["trade"]["symbol"] == "OP"


def test_closer_notes_and_retries_half_leg(monkeypatch, tmp_path):
    from backend.services import exchange_closer_claw_service as closer

    monkeypatch.setenv("CLOSER_CLAW_ENABLED", "1")
    monkeypatch.setenv("CLOSER_DUST_ENABLED", "0")
    monkeypatch.setattr(closer, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(closer, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(closer, "_OPEN_PATH", str(tmp_path / "open.json"))

    leg = closer.note_execution_legs(
        {"symbol": "ADA", "buy_venue": "binance", "sell_venue": "nonkyc", "notional_usd": 12},
        {
            "success": False,
            "quantity": 10.0,
            "notional_usd": 12.0,
            "executed_at": "2026-11-13T08:00:00Z",
            "buy_order": {"success": True, "order_id": "b1"},
            "sell_order": {"success": False, "error": "insufficient"},
        },
        source="test",
    )
    assert leg is not None
    assert leg["missing"] == "sell"
    assert len(closer._load_open()) == 1

    monkeypatch.setattr(
        closer,
        "_retry_open_leg",
        lambda row: {"success": True, "venue": "nonkyc", "side": "sell", "symbol": "ADA"},
    )
    out = closer.run_closer_tick(force=True)
    assert out["closed"] == 1
    assert out["open_after"] == 0


def test_raise_candidates_skip_ld_wrappers():
    from backend.services import exchange_spread_hunter_arm_service as hunt

    bals = {"USDC": 1.0, "LDADA": 100.0, "LDALGO": 50.0, "XRP": 3.0, "DKK": 1.0}
    ordered = hunt._raise_inventory_candidates(bals, quote="USDC", preferred=["ADA"])
    assert "LDADA" not in ordered
    assert "LDALGO" not in ordered
    assert "DKK" not in ordered
    assert ordered[0] == "XRP" or "XRP" in ordered


def test_raise_continues_after_failed_order(monkeypatch, tmp_path):
    from backend.services import exchange_spread_hunter_arm_service as hunt

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.venue_quote_asset",
        lambda v: "USDC",
    )
    bals = {"USDC": 1.0, "XRP": 10.0, "ADA": 100.0}
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.parse_spot_balances",
        lambda *a, **k: dict(bals),
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.invalidate_venue_balance_cache",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        hunt.conn,
        "fetch_ticker",
        lambda venue, sym: {"bid": 2.0, "ask": 2.01},
    )
    calls = {"n": 0}

    def fake_order(venue, sym, side, qty, **kw):
        calls["n"] += 1
        if sym == "XRP":
            return {"success": False, "error": "boom"}
        return {"success": True, "order_id": "ok"}

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.place_market_order",
        fake_order,
    )
    monkeypatch.setattr(
        "backend.services.exchange_binance_earn_service.list_ld_balances",
        lambda *a, **k: [],
    )
    out = hunt._raise_quote_on_buy_venue(
        "binance", need_usd=20.0, raise_symbols=["XRP", "ADA"], min_sell_usd=3.0, scan_all_balances=False,
    )
    assert out["success"] is True
    assert out["symbol"] == "ADA"
    assert calls["n"] == 2


def test_courier_keeps_binance_as_poor_when_under_floor():
    from backend.services import exchange_courier_arm_service as courier

    imb = courier._imbalance(
        [
            {"venue": "binance", "quote": "USDC", "free": 0.45},
            {"venue": "nonkyc", "quote": "USDT", "free": 0.40},
        ],
        floor=12.0,
    )
    assert imb["poor"]["venue"] == "binance"
    assert imb["keep_binance"] is True


def test_ld_underlying_map():
    from backend.services.exchange_binance_earn_service import _ld_underlying, list_ld_balances

    assert _ld_underlying("LDADA") == "ADA"
    assert _ld_underlying("LDALGO") == "ALGO"
    assert _ld_underlying("ADA") is None
    rows = list_ld_balances({"LDADA": 10.0, "USDC": 1.0, "XRP": 2.0})
    assert rows and rows[0]["asset"] == "ADA"


def test_head_enables_new_limbs(monkeypatch, tmp_path):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_head_service as head

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    (tmp_path / "logs").mkdir()
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(head, "_CONTROL_PATH", str(data / "profit_head_control.json"))
    monkeypatch.setattr(head, "_STATE_PATH", str(data / "profit_head_state.json"))
    monkeypatch.setattr(head, "_LEDGER_PATH", str(data / "profit_head_ledger.jsonl"))
    monkeypatch.setattr(
        head,
        "_HEARTBEAT_CANDIDATES",
        [str(tmp_path / "logs" / "daemon_all_profit_heartbeat.json")],
    )
    monkeypatch.setattr(
        head,
        "_venue_quote_snapshot",
        lambda: {
            "binance": {"ok": True, "quote": "USDC", "free": 2.0},
            "nonkyc": {"ok": True, "quote": "USDT", "free": 30.0},
        },
    )
    monkeypatch.setattr(head, "_pbook_top", lambda: None)
    monkeypatch.setattr(head, "_search_hot_symbols", lambda: [])
    monkeypatch.setattr(
        head,
        "_read_heartbeat",
        lambda: {"loops": {"hunter": {"summary": "skip=regime_skew_too_wide qual=3"}}},
    )
    res = head.run_head_tick(force=True)
    assert res["limbs"]["courier"]["enabled"] is True
    assert res["limbs"]["latch"]["enabled"] is True
    assert res["limbs"]["closer"]["enabled"] is True
    assert any(d.startswith("tool:latch_armed") for d in res["decisions"])
