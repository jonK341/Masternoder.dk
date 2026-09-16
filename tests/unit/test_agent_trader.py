"""Agent trader service tests."""
import pytest


@pytest.fixture
def market_env(tmp_path, monkeypatch):
    from backend.services import p2p_market_service as pm
    from backend.services import agent_wallet_service as aw
    from backend.services import unified_points_database as upd
    from backend.services import mn2_staking_service as staking
    from contextlib import contextmanager

    staking_tmp = tmp_path / "staking_data"
    staking_tmp.mkdir()
    monkeypatch.setattr(staking, "_data_dir", lambda: str(staking_tmp))
    import json
    (staking_tmp / "mn2_staking_config.json").write_text(json.dumps({
        "enabled": True,
        "trader_agents": {
            "enabled": True,
            "keep_balance_min_mn2": 100,
            "market": {
                "enabled": True,
                "sell_mn2_per_order": 10,
                "fill_mn2_per_trade": 5,
                "min_free_mn2": 5,
                "coin_float_target": 500,
                "max_open_sells_per_agent": 2,
                "reference_price_coins_per_mn2": 100,
            },
        },
    }), encoding="utf-8")

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)

    def _file_only_get(user_id: str):
        return {"success": True, "points": db._points_payload_from_file(user_id)}

    monkeypatch.setattr(db, "get_all_points", _file_only_get)

    monkeypatch.setattr(pm, "_ORDERS", str(tmp_path / "orders.json"))
    monkeypatch.setattr(pm, "_TRADES", str(tmp_path / "trades.jsonl"))
    monkeypatch.setattr(aw, "_WALLETS_FILE", str(tmp_path / "wallets.json"))
    treasury_path = tmp_path / "agent_treasury.json"
    treasury_path.write_text('{"trader_agent_count": 2}', encoding="utf-8")
    monkeypatch.setattr(aw, "_TREASURY_FILE", str(treasury_path))
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})
    monkeypatch.setattr(
        "backend.services.agent_kill_switch.check_action",
        lambda verb, agent_id=None: {"allowed": True},
    )

    for aid in ("trader_agent_1", "trader_agent_2"):
        db.add_points(aid, "mn2_balance", 500.0, source="seed", metadata={"reference": f"seed-{aid}"})
        from backend.services.agent_wallet_service import credit
        credit(aid, 500.0, reference=f"seed-wallet-{aid}", source="test")
    return db


def test_list_strategies():
    from backend.services.agent_trader_service import list_strategies
    s = list_strategies()
    assert "market_maker" in s
    assert len(s) >= 4


def test_run_trader_sell_places_order(market_env):
    from backend.services.agent_trader_service import run_trader_sell_tick
    from backend.services.p2p_market_service import list_orders

    r = run_trader_sell_tick(agent_id="trader_agent_1", strategy="market_maker")
    assert r.get("success") is True
    assert not r.get("skipped") or r.get("reason") != "insufficient_free_mn2"
    orders = list_orders(side="sell").get("orders") or []
    assert any(o.get("user_id") == "trader_agent_1" for o in orders)


def test_run_all_traders_cross_fill(market_env):
    from backend.services.agent_trader_service import run_all_traders
    from backend.services.p2p_market_service import list_orders

    r = run_all_traders()
    assert r.get("success") is True
    assert r.get("trades", 0) >= 1
    sells = list_orders(side="sell").get("orders") or []
    assert sells
