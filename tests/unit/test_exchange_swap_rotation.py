"""Swap rotation service — funding gap analysis, suggestions, dry-run execute."""
import json

import pytest


@pytest.fixture
def rotation_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import exchange_swap_rotation_service as rot

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    cfg_path = data / "profit_path_protocol.json"
    ledger_path = data / "profit_path_ledger.jsonl"

    monkeypatch.setattr(ppp, "_CFG_PATH", str(cfg_path))
    monkeypatch.setattr(ppp, "_LEDGER_PATH", str(ledger_path))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(rot, "load_config", ppp.load_config)

    (data / "profit_path_protocol.json").write_text(
        json.dumps({"enabled": True, "rotation_live_enabled": False}),
        encoding="utf-8",
    )

    return {"ppp": ppp, "rot": rot, "ledger_path": ledger_path, "data": data}


def test_analyze_funding_gaps_short_buy_leg(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    ppp = rotation_env["ppp"]

    def fake_can_fund(venue_id, symbol, side, *, qty, notional_usd, buffer_pct=0.03):
        if side == "buy":
            return {"ok": False, "venue_id": venue_id, "side": "buy", "asset": "USDC", "free": 50.0, "need": 80.0}
        return {"ok": True, "venue_id": venue_id, "side": "sell", "asset": symbol, "free": 1.0, "need": qty}

    def fake_max_funded(*args, **kwargs):
        return 50.0

    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.can_fund_arb_leg",
        fake_can_fund,
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.max_funded_notional_usd",
        fake_max_funded,
    )
    monkeypatch.setattr(
        rot,
        "_resolve_route",
        lambda aid, sym: ("binance", "nonkyc", 50000.0, 75.0),
    )

    out = rot.analyze_funding_gaps("arb_agent_btc_eth", "BTC", 75.0)
    assert out["success"] is True
    assert out["funded_ok"] is False
    assert len(out["short_legs"]) == 1
    assert out["short_legs"][0]["leg"] == "buy"
    assert out["max_funded_usd"] == 50.0


def test_suggest_swap_actions_from_ledger(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    ppp = rotation_env["ppp"]

    ppp.record_scan(
        agent_id="arb_agent_btc_eth",
        best={
            "symbol": "BTC",
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "gross_bps": 40,
            "fee_bps": 20,
            "net_bps": 20,
        },
        decision="skip",
        skip_reason="insufficient_venue_balance",
        notional_usd=75.0,
        venues=["binance", "nonkyc"],
    )

    monkeypatch.setattr(
        rot,
        "analyze_funding_gaps",
        lambda aid, sym, notion: {
            "success": True,
            "short_legs": [{"leg": "buy", "venue_id": "binance", "asset": "USDC", "free": 50, "need": 80}],
            "quantity": 0.001,
            "buy_ask": 50000,
            "max_funded_usd": 50,
        },
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.venue_has_credentials",
        lambda vid: vid == "binance",
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.parse_spot_balances",
        lambda vid, dry_run=False: {"USDC": 79.0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.venue_quote_asset",
        lambda vid: "USDC",
    )

    out = rot.suggest_swap_actions(hours=24, limit=5)
    assert out["success"] is True
    assert out["funding_skip_count"] >= 1
    assert out["action_count"] >= 1
    types = {a["type"] for a in out["actions"]}
    assert "external_market_buy" in types or "reduce_notional" in types


def test_execute_rotation_dry_run_internal(rotation_env, monkeypatch):
    rot = rotation_env["rot"]

    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.ex.quote_swap",
        lambda uid, sym, side, amt, quote: {
            "success": True,
            "quote_id": "q1",
            "symbol": sym,
            "side": side,
            "amount": amt,
            "quote_currency": quote,
            "quote_cost": amt,
        },
    )

    action = {
        "type": "internal_stable_swap",
        "wallet_user_id": "exchange_sales_pool",
        "symbol": "USDC",
        "side": "buy",
        "quote": "USDT",
        "amount": 25.0,
    }
    res = rot.execute_rotation(action, dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["mode"] == "internal"


def test_execute_rotation_external_requires_live_flag(rotation_env, monkeypatch):
    rot = rotation_env["rot"]

    monkeypatch.setattr(rot, "rotation_live_enabled", lambda: False)
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.place_market_order",
        lambda venue, sym, side, qty, dry_run=None, **kw: {"success": True, "mode": "paper", "simulated": True},
    )

    action = {
        "type": "external_market_buy",
        "venue_id": "binance",
        "symbol": "BTC",
        "side": "buy",
        "amount_usd": 50,
        "quantity": 0.001,
    }
    res = rot.execute_rotation(action, dry_run=False)
    assert res["dry_run"] is True
    assert res["mode"] == "paper"
    assert "hint" in res


def test_execute_rotation_advisory_reduce_notional(rotation_env):
    rot = rotation_env["rot"]
    action = {
        "type": "reduce_notional",
        "venue_id": "binance",
        "suggested_notional_usd": 75,
    }
    res = rot.execute_rotation(action, dry_run=True)
    assert res["success"] is True
    assert res["skipped"] is True


def test_suggest_quote_shortfall_prefers_reduce_notional_over_doge(rotation_env, monkeypatch):
    """Quote shortfall must not sell protected DOGE sell-leg inventory — prefer reduce_notional."""
    rot = rotation_env["rot"]
    ppp = rotation_env["ppp"]

    ppp.record_scan(
        agent_id="arb_agent_btc_eth",
        best={"symbol": "LINK", "buy_venue": "nonkyc", "sell_venue": "binance", "net_bps": 20},
        decision="skip",
        skip_reason="insufficient_venue_balance",
        notional_usd=95.0,
        venues=["binance", "nonkyc"],
    )

    monkeypatch.setattr(
        rot,
        "analyze_funding_gaps",
        lambda aid, sym, notion: {
            "success": True,
            "notional_usd": notion,
            "short_legs": [{
                "leg": "buy",
                "venue_id": "nonkyc",
                "asset": "USDT",
                "free": 86.0,
                "need": 98.0,
            }],
            "quantity": 1.0,
            "buy_ask": 7.5,
            "max_funded_usd": 83,
        },
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.venue_has_credentials",
        lambda vid: vid == "nonkyc",
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.parse_spot_balances",
        lambda vid, dry_run=False: {"USDT": 86.0, "DOGE": 200.0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.venue_quote_asset",
        lambda vid: "USDT",
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.ex._price_usd",
        lambda sym: {"DOGE": 0.15, "LINK": 7.5}.get(str(sym).upper(), 1.0),
    )
    monkeypatch.setattr(rot, "_active_sell_leg_symbols", lambda vid: frozenset({"DOGE"}))

    out = rot.suggest_swap_actions(hours=24, limit=5)
    top = (out.get("actions") or [{}])[0]
    assert top.get("type") == "reduce_notional"
    assert "DOGE" not in top.get("label", "")


def test_execute_rotation_propagates_venue_error(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    monkeypatch.setattr(rot, "rotation_live_enabled", lambda: True)
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.place_market_order",
        lambda venue, sym, side, qty, dry_run=None, rotation=False, **kw: {
            "success": False,
            "status_code": 400,
            "body": {"error": {"description": "Insufficient funds for order creation"}},
        },
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.market_order_for_leg",
        lambda venue, leg, sym, usd, **kw: {
            "ok": True,
            "venue_id": venue,
            "base": sym,
            "quote": "USDT",
            "market": f"{sym}_USDT",
            "side": leg,
            "quantity": kw.get("quantity") or 100.0,
        },
    )

    action = {
        "type": "external_market_buy",
        "venue_id": "nonkyc",
        "symbol": "DOGE",
        "side": "buy",
        "amount_usd": 20,
        "quantity": 100,
    }
    res = rot.execute_rotation(action, dry_run=False)
    assert res["success"] is False
    assert "Insufficient funds" in str(res.get("error") or "")


def test_rotation_auto_execute_dedupe(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    ppp = rotation_env["ppp"]
    data = rotation_env["data"]
    cfg_path = data / "profit_path_protocol.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.update({
        "rotation_auto_execute": True,
        "rotation_live_enabled": True,
        "rotation_auto_max_usd_per_tick": 100,
        "rotation_auto_types": ["external_market_buy"],
    })
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    state_path = str(data / "rotation_auto_state.json")
    monkeypatch.setattr(rot, "_STATE_PATH", state_path)

    action = {
        "type": "external_market_buy",
        "venue_id": "nonkyc",
        "symbol": "USDT",
        "side": "buy",
        "amount_usd": 98,
        "label": "Buy USDT on nonkyc ~$98",
        "priority": "high",
        "priority_score": 5,
    }

    monkeypatch.setattr(rot, "suggest_swap_actions", lambda **kw: {"actions": [action]})
    monkeypatch.setattr(rot, "rotation_auto_execute_enabled", lambda: True)
    monkeypatch.setattr(rot, "rotation_live_enabled", lambda: True)
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.market_order_for_leg",
        lambda venue, leg, sym, usd, **kw: {
            "ok": True,
            "venue_id": venue,
            "base": sym,
            "quote": "USDT",
            "market": f"{sym}_USDT",
            "side": leg,
            "quantity": 100.0,
        },
    )
    monkeypatch.setattr(
        rot,
        "execute_rotation",
        lambda act, dry_run=True: {"success": False, "error": "pair_not_supported:USDT on nonkyc", "mode": "live"},
    )
    monkeypatch.setattr(rot, "log_rotation_to_ppp", lambda *a, **k: None)

    res1 = rot.maybe_auto_rotation({"platform": {"results": {"arbitrage": {"executed_count": 0}}}})
    assert res1.get("auto_executed") is True
    assert res1.get("success") is False

    res2 = rot.maybe_auto_rotation({"platform": {"results": {"arbitrage": {"executed_count": 0}}}})
    assert res2.get("skipped") is True
    assert res2.get("reason") == "recent_failure_dedupe"


def test_dedupe_venue_asset_cooldown(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    action = {
        "type": "external_market_buy",
        "venue_id": "nonkyc",
        "symbol": "USDT",
        "side": "buy",
        "amount_usd": 98,
    }
    state = {
        "recent": [{
            "ts": rot._iso(),
            "asset_key": rot._venue_asset_key(action),
            "amount_usd": 97,
            "success": True,
        }],
    }
    assert rot._dedupe_skip(action, state) == "venue_asset_cooldown"

    action2 = dict(action)
    action2["amount_usd"] = 150
    assert rot._dedupe_skip(action2, state) is None


def test_dedupe_allows_insufficient_balance_retry(rotation_env):
    rot = rotation_env["rot"]
    action = {
        "type": "external_market_buy",
        "venue_id": "binance",
        "symbol": "LINK",
        "side": "buy",
        "amount_usd": 83,
        "market": "LINKUSDC",
    }
    state = {
        "last_failure_hash": rot._action_fingerprint(action),
        "last_failure_at": rot._iso(),
        "last_failure_reason": "Account has insufficient balance for requested action.",
    }
    assert rot._dedupe_skip(action, state) is None


def test_suggest_doge_sell_leg_resolves_market(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    ppp = rotation_env["ppp"]

    ppp.record_scan(
        agent_id="arb_agent_meme",
        best={"symbol": "DOGE", "buy_venue": "binance", "sell_venue": "nonkyc", "net_bps": 25},
        decision="skip",
        skip_reason="insufficient_venue_balance",
        notional_usd=75.0,
        venues=["binance", "nonkyc"],
    )

    monkeypatch.setattr(
        rot,
        "analyze_funding_gaps",
        lambda aid, sym, notion: {
            "success": True,
            "notional_usd": notion,
            "short_legs": [{
                "leg": "sell",
                "venue_id": "nonkyc",
                "asset": "DOGE",
                "free": 0.0,
                "need": 500.0,
            }],
            "quantity": 500.0,
            "buy_ask": 0.15,
            "max_funded_usd": 0,
        },
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.venue_has_credentials",
        lambda vid: vid == "nonkyc",
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.parse_spot_balances",
        lambda vid, dry_run=False: {"USDT": 100.0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.market_order_for_leg",
        lambda venue, leg, sym, usd, **kw: {
            "ok": True,
            "venue_id": venue,
            "base": "DOGE",
            "quote": "USDT",
            "market": "DOGE_USDT",
            "side": "buy",
            "quantity": 200.0,
        },
    )

    out = rot.suggest_swap_actions(hours=24, limit=5)
    top = (out.get("actions") or [{}])[0]
    assert top.get("symbol") == "DOGE"
    assert top.get("side") == "buy"
    assert "DOGE" in top.get("label", "")
    assert "DOGE_USDT" in top.get("label", "")
    assert "Buy USDT" not in top.get("label", "")


def test_execute_rotation_skips_unsupported_pair(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.market_order_for_leg",
        lambda *a, **kw: {"ok": False, "error": "pair_not_supported:DOGE on bitstamp"},
    )
    action = {
        "type": "external_market_buy",
        "venue_id": "bitstamp",
        "symbol": "DOGE",
        "side": "buy",
        "amount_usd": 25,
    }
    res = rot.execute_rotation(action, dry_run=False)
    assert res["success"] is False
    assert "pair_not_supported:DOGE" in str(res.get("error") or "")


def test_reduce_notional_already_applied(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    data = rotation_env["data"]
    conn_path = data.parent / "exchange_connectors_config.json"
    conn_path.write_text(
        '{"paper_trade_usd": 50, "arbitrage_agents": [{"id": "a1", "venues": ["binance"], "paper_trade_usd": 50}]}',
        encoding="utf-8",
    )
    ext_path = data.parent / "exchange_extended_profit_config.json"
    ext_path.write_text('{"strategies": {}}', encoding="utf-8")
    monkeypatch.setattr(rot, "_CONNECTORS_PATH", str(conn_path))
    monkeypatch.setattr(rot, "_EXTENDED_PROFIT_PATH", str(ext_path))

    action = {"type": "reduce_notional", "venue_id": "binance", "suggested_notional_usd": 75}
    res = rot.execute_rotation(action, dry_run=False)
    assert res["success"] is True
    assert res.get("already_applied") is True
    assert res.get("updated") == []


def test_execute_rotation_blocks_sell_below_min_leg_reserve(rotation_env, monkeypatch):
    rot = rotation_env["rot"]
    monkeypatch.setattr(rot, "rotation_live_enabled", lambda: True)
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.market_order_for_leg",
        lambda *a, **kw: {
            "ok": True,
            "base": "DOGE",
            "quantity": 40.0,
            "market": "DOGE_USDT",
            "quote": "USDT",
            "notional_usd": 6.0,
            "price_usd": 0.15,
        },
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.vapi.parse_spot_balances",
        lambda vid, dry_run=False: {"DOGE": 200.0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.ex._price_usd",
        lambda sym: 0.15 if sym == "DOGE" else 0,
    )
    monkeypatch.setattr(rot, "load_config", lambda: {"min_sell_leg_usd": 25})

    action = {
        "type": "external_market_sell",
        "venue_id": "nonkyc",
        "symbol": "DOGE",
        "side": "sell",
        "amount_usd": 6.0,
        "quantity": 40.0,
    }
    res = rot.execute_rotation(action, dry_run=False)
    assert res.get("skipped") is True
    assert res.get("error") == "sell_would_breach_min_leg_reserve"

