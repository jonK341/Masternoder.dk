"""Unit tests for the constant spread-hunter arm."""
from __future__ import annotations

from backend.services import exchange_spread_hunter_arm_service as hunt


def test_compounded_leg_positive_edge():
    math = hunt.estimate_compounded_leg(
        buy_ask=1.0,
        sell_bid=1.02,
        notional_usd=100.0,
        fee_buy_bps=10,
        fee_sell_bps=20,
        xfer_bps=6,
    )
    assert math["gross_bps"] == 200.0
    assert math["fee_bps"] == 36.0
    assert math["net_bps"] == 164.0
    assert math["est_profit_usd"] > 0
    assert math["profitable"] is True


def test_compounded_leg_fees_wipe_edge():
    math = hunt.estimate_compounded_leg(
        buy_ask=1.0,
        sell_bid=1.001,
        notional_usd=100.0,
        fee_buy_bps=10,
        fee_sell_bps=20,
        xfer_bps=6,
    )
    assert math["net_bps"] < 0
    assert math["profitable"] is False


def test_regime_deweight_collapses():
    factor, reason = hunt.regime_deweight_factor(
        net_bps=5.0, mid_skew=10.0, max_skew_bps=80.0, collapse_bps=8.0,
    )
    assert factor == 0.0
    assert reason == "regime_edge_collapsed"


def test_regime_deweight_wide_skew():
    factor, reason = hunt.regime_deweight_factor(
        net_bps=20.0, mid_skew=160.0, max_skew_bps=80.0, collapse_bps=8.0,
    )
    assert factor == 0.0
    assert reason == "regime_skew_too_wide"


def test_regime_partial_deweight():
    factor, reason = hunt.regime_deweight_factor(
        net_bps=20.0, mid_skew=120.0, max_skew_bps=80.0, collapse_bps=8.0,
    )
    assert 0.0 < factor < 1.0
    assert reason == "regime_deweight"


def test_arm_disabled_skips(monkeypatch):
    monkeypatch.setenv("SPREAD_HUNTER_ENABLED", "0")
    out = hunt.run_spread_hunter_tick()
    assert out.get("skipped") is True
    assert out.get("reason") == "arm_disabled"


def test_hunter_executes_after_recheck(monkeypatch, tmp_path):
    monkeypatch.setenv("SPREAD_HUNTER_ENABLED", "1")
    monkeypatch.setenv("SPREAD_HUNTER_PREFUND", "0")
    monkeypatch.setenv("SPREAD_HUNTER_BACKFILL", "0")
    monkeypatch.setenv("SPREAD_HUNTER_MIN_BPS", "12")
    monkeypatch.setenv("SPREAD_HUNTER_MIN_PROFIT_USD", "0.01")
    monkeypatch.setenv("SPREAD_HUNTER_NOTIONAL_USD", "15")
    monkeypatch.setenv("SPREAD_HUNTER_SCAN_LIMIT", "20")
    monkeypatch.setattr(hunt, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(hunt, "_BOARD_PATH", str(tmp_path / "board.json"))
    monkeypatch.setattr(hunt.arb, "live_enabled", lambda: False)
    monkeypatch.setattr(
        hunt,
        "_build_universe",
        lambda **kw: {"symbols": ["ADA", "LINK"], "catalog_count": 2, "hot_count": 0, "scan_limit": 20},
    )

    opp = {
        "symbol": "ADA",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "buy_ask": 0.17,
        "sell_bid": 0.175,
        "net_bps": 20.0,
        "est_profit_usd": 0.03,
        "notional_usd": 15.0,
        "profitable": True,
    }
    monkeypatch.setattr(
        hunt,
        "_batch_scan",
        lambda *a, **k: [{
            **opp,
            "gross_bps": 294.12,
            "fee_bps": 36.0,
            "net_bps": 258.0,
            "est_profit_usd": 0.38,
            "compounded": True,
            "profitable": True,
        }],
    )
    monkeypatch.setattr(
        hunt,
        "_recheck_live",
        lambda o, **kw: {
            "ok": True,
            "opportunity": {
                **o,
                "regime_factor": 1.0,
                "mid_skew_bps": 12.0,
                "net_bps": 40.0,
                "est_profit_usd": 0.06,
                "profitable": True,
            },
        },
    )
    monkeypatch.setattr(
        hunt.arb,
        "prepare_live_opportunity",
        lambda o, **kw: {"ok": True, "opportunity": dict(o)},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: None,
    )
    calls = {"exec": 0}

    def fake_exec(o, agent_id=None, dry_run=False):
        calls["exec"] += 1
        return {"success": True, "mode": "paper"}

    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.execute_spatial_arbitrage",
        fake_exec,
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.book_agent_profit",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_scan",
        lambda **kw: "path-hunt-1",
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_execution",
        lambda **kw: None,
    )

    out = hunt.run_spread_hunter_tick(force=True)
    assert out["executed"] is True
    assert out["qualifying"] == 1
    assert out["top"]["symbol"] == "ADA"
    assert calls["exec"] == 1


def test_hunter_skips_when_recheck_collapses(monkeypatch, tmp_path):
    monkeypatch.setenv("SPREAD_HUNTER_ENABLED", "1")
    monkeypatch.setenv("SPREAD_HUNTER_PREFUND", "0")
    monkeypatch.setenv("SPREAD_HUNTER_BACKFILL", "0")
    monkeypatch.setenv("SPREAD_HUNTER_MIN_BPS", "12")
    monkeypatch.setattr(hunt, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(hunt, "_BOARD_PATH", str(tmp_path / "board.json"))
    monkeypatch.setattr(hunt.arb, "live_enabled", lambda: True)
    monkeypatch.setattr(
        hunt,
        "_build_universe",
        lambda **kw: {"symbols": ["LINK"], "catalog_count": 1, "hot_count": 0, "scan_limit": 10},
    )
    monkeypatch.setattr(
        hunt,
        "_batch_scan",
        lambda *a, **k: [{
            "symbol": "LINK",
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "buy_ask": 10.0,
            "sell_bid": 10.05,
            "net_bps": 18.0,
            "est_profit_usd": 0.03,
            "notional_usd": 15.0,
            "profitable": True,
        }],
    )
    monkeypatch.setattr(
        hunt,
        "_recheck_live",
        lambda *a, **k: {"ok": False, "reason": "regime_edge_collapsed"},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: None,
    )

    out = hunt.run_spread_hunter_tick(force=True)
    assert out["executed"] is False
    assert out["skip_reason"] == "regime_edge_collapsed"


def test_hunter_prefers_prefund_wheel(monkeypatch, tmp_path):
    monkeypatch.setenv("SPREAD_HUNTER_ENABLED", "1")
    monkeypatch.setenv("SPREAD_HUNTER_PREFUND", "1")
    monkeypatch.setenv("SPREAD_HUNTER_BACKFILL", "0")
    monkeypatch.setenv("SPREAD_HUNTER_MIN_BPS", "12")
    monkeypatch.setenv("TECH_EXECUTOR_ENABLED", "0")
    monkeypatch.setattr(hunt, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(hunt, "_BOARD_PATH", str(tmp_path / "board.json"))
    monkeypatch.setattr(hunt.arb, "live_enabled", lambda: True)
    monkeypatch.setattr(
        "backend.services.exchange_technique_executor_service.execute_techniques_for_opportunity",
        lambda opp, **kw: {
            "success": False,
            "ready": False,
            "opportunity": opp,
            "applied": [],
            "skipped": True,
            "reason": "executor_disabled",
        },
    )
    monkeypatch.setattr(
        hunt,
        "_build_universe",
        lambda **kw: {"symbols": ["BNB"], "catalog_count": 1, "hot_count": 0, "scan_limit": 10},
    )
    opp = {
        "symbol": "BNB",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "buy_ask": 500.0,
        "sell_bid": 505.0,  # ~100 bps gross so compounded fees still clear gates
        "net_bps": 60.0,
        "est_profit_usd": 0.09,
        "notional_usd": 15.0,
        "profitable": True,
        "gross_bps": 100.0,
        "fee_bps": 36.0,
    }
    monkeypatch.setattr(hunt, "_batch_scan", lambda *a, **k: [opp])
    monkeypatch.setattr(
        hunt,
        "_recheck_live",
        lambda o, **kw: {
            "ok": True,
            "opportunity": {
                **o,
                "regime_factor": 1.0,
                "mid_skew_bps": 8.0,
                "net_bps": 60.0,
                "est_profit_usd": 0.09,
                "profitable": True,
            },
        },
    )
    prepares = [
        {"ok": False, "reason": "insufficient_venue_balance", "requested_usd": 15.0, "max_funded_usd": 2.0},
        {"ok": True, "opportunity": dict(opp)},
    ]

    def fake_prepare(o, **kw):
        return prepares.pop(0)

    monkeypatch.setattr(hunt.arb, "prepare_live_opportunity", fake_prepare)
    monkeypatch.setattr(
        hunt,
        "_try_fund_wheel",
        lambda *a, **k: {"success": True, "steps": [{"step": "raise_quote", "action": "prefund_sell"}]},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.execute_spatial_arbitrage",
        lambda *a, **k: {"success": True, "mode": "live"},
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.book_agent_profit",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_scan",
        lambda **kw: "path-hunt-2",
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_execution",
        lambda **kw: None,
    )

    out = hunt.run_spread_hunter_tick(force=True)
    assert out["executed"] is True
    assert out["prefund"]["success"] is True


def test_backfill_needed_on_head_hint():
    need, why = hunt._backfill_needed(
        floor_usd=18.0,
        hint={"symbol": "OP", "technique": "prefund_buy_quote"},
        last_skip=None,
        snaps=[{"venue": "binance", "free": 50.0}, {"venue": "nonkyc", "free": 50.0}],
    )
    assert need is True
    assert why == "head_prefund_hint"


def test_backfill_needed_on_thin_total():
    need, why = hunt._backfill_needed(
        floor_usd=18.0,
        hint=None,
        last_skip=None,
        snaps=[{"venue": "binance", "free": 4.0}, {"venue": "nonkyc", "free": 6.0}],
    )
    assert need is True
    assert why == "thin_total_quote"


def test_decide_assignments_includes_backfill(monkeypatch, tmp_path):
    monkeypatch.setenv("SPREAD_HUNTER_BACKFILL", "1")
    monkeypatch.setattr(hunt, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(
        hunt,
        "_backfill_needed",
        lambda **kw: (True, "thin_total_quote"),
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_head_service.get_prefund_hint",
        lambda: {"symbol": "FET", "reason": "unfunded_top_edge"},
    )
    plan = hunt.decide_hunter_assignments(state={})
    assert plan["assignments"] == ["backfill", "hunt"]
    assert plan["hint"]["symbol"] == "FET"


def test_hunter_runs_backfill_assignment_before_hunt(monkeypatch, tmp_path):
    monkeypatch.setenv("SPREAD_HUNTER_ENABLED", "1")
    monkeypatch.setenv("SPREAD_HUNTER_PREFUND", "0")
    monkeypatch.setenv("SPREAD_HUNTER_BACKFILL", "1")
    monkeypatch.setenv("SPREAD_HUNTER_MIN_BPS", "12")
    monkeypatch.setattr(hunt, "_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(hunt, "_BOARD_PATH", str(tmp_path / "board.json"))
    monkeypatch.setattr(hunt, "_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(hunt.arb, "live_enabled", lambda: True)
    monkeypatch.setattr(
        hunt,
        "decide_hunter_assignments",
        lambda **kw: {
            "assignments": ["backfill", "hunt"],
            "backfill_needed": True,
            "backfill_ready": True,
            "reason": "head_prefund_hint",
            "hint": {"symbol": "OP", "technique": "prefund_buy_quote"},
            "floor_usd": 18.0,
        },
    )
    calls = {"bf": 0}

    def fake_bf(**kw):
        calls["bf"] += 1
        return {
            "success": True,
            "assignment": "backfill",
            "raised_usd": 8.5,
            "reason": "raised",
            "total_free_usd": 19.2,
            "actions": [],
        }

    monkeypatch.setattr(hunt, "run_hunter_backfill_assignment", fake_bf)
    monkeypatch.setattr(
        hunt,
        "_build_universe",
        lambda **kw: {"symbols": ["OP"], "catalog_count": 1, "hot_count": 0, "scan_limit": 10},
    )
    monkeypatch.setattr(hunt, "_batch_scan", lambda *a, **k: [])
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: None,
    )

    out = hunt.run_spread_hunter_tick(force=True)
    assert calls["bf"] == 1
    assert out["assignments"] == ["backfill", "hunt"]
    assert out["backfill"]["raised_usd"] == 8.5
    assert out["skip_reason"] == "no_external_spreads"


def test_raise_inventory_candidates_prefers_hint_then_extras():
    bals = {"USDC": 2.0, "OP": 10.0, "ADA": 100.0, "WEIRD": 50.0}
    ordered = hunt._raise_inventory_candidates(bals, quote="USDC", preferred=["OP"])
    assert ordered[0] == "OP"
    assert "ADA" in ordered
    assert "WEIRD" in ordered
    assert "USDC" not in ordered
