"""Swap rotation service — funding gap analysis, suggestions, dry-run execute."""
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

    return {"ppp": ppp, "rot": rot, "ledger_path": ledger_path}


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
        lambda venue, sym, side, qty, dry_run=None: {"success": True, "mode": "paper", "simulated": True},
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
