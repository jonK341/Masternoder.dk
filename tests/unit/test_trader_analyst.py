"""Pre-trade analyst readiness logic."""
from trader_app.analyst import analyze


def _cfg(**kw):
    base = {"order_size_usd": 6.0, "min_notional_usd": 5.0, "hard_loss_cap_usd": 5.0, "assets": ["DOGE"]}
    base.update(kw)
    return base


def test_blocked_when_gates_off_and_unfunded():
    r = analyze(
        gates={"grid_live": False},
        balances={"venues": {"binance": {"assets": [{"symbol": "USDC", "usd_value": 0.0}]}}},
        signals={"signals": []},
        grid_status_data={"enabled": False},
        grid_config=_cfg(),
    )
    assert r["ready"] is False
    assert r["verdict"] == "blocked"
    assert r["blocker_count"] >= 3  # gates, funding, enabled
    assert r["actions"]  # has prioritized actions
    assert not any(c["ok"] for c in r["checks"] if c["name"] == "Live gates enabled")


def test_ready_when_all_pass():
    r = analyze(
        gates={"grid_live": True},
        balances={"venues": {"binance": {"assets": [{"symbol": "USDC", "usd_value": 50.0}]}}},
        signals={"signals": [{"actionable": True}]},
        grid_status_data={"enabled": True},
        grid_config=_cfg(),
    )
    assert r["ready"] is True
    assert r["verdict"] == "ready_to_auto_trade"
    assert "grid_bot_daemon" in r["next_step"]
    assert r["funded_any_venue"] is True


def test_order_size_below_min_notional_flagged():
    r = analyze(
        gates={"grid_live": True},
        balances={"venues": {"binance": {"assets": [{"symbol": "USDC", "usd_value": 50.0}]}}},
        signals={"signals": [{"actionable": True}]},
        grid_status_data={"enabled": True},
        grid_config=_cfg(order_size_usd=2.0, min_notional_usd=5.0),
    )
    assert r["ready"] is False
    assert any((not c["ok"]) and c["name"] == "Order size >= min notional" for c in r["checks"])
