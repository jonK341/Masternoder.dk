"""Extended profit strategy tests."""
import pytest


@pytest.fixture
def ext_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import external_exchange_connector_service as conn
    from backend.services import exchange_extended_profit_service as ext

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(conn, "_PRICE_CACHE_PATH", str(data / "external_prices.json"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(ext, "_CFG_PATH", str(tmp_path / "exchange_extended_profit_config.json"))
    monkeypatch.setattr(ext, "_THRESHOLD_STATE_PATH", str(data / "arb_threshold_state.json"))
    (tmp_path / "exchange_extended_profit_config.json").write_text(
        '{"enabled":true,"profiles":{"standard":{"strategies":["stablecoin_peg","triangular_paper"]}},'
        '"strategies":{"stablecoin_peg":{"enabled":true,"min_deviation_bps":1,"notional_usd":100,"agent_id":"t1"},'
        '"triangular_paper":{"enabled":true,"venues":["binance"],"loops":[["BTC","ETH","SOL"]],'
        '"min_edge_bps":1,"notional_usd":50,"agent_id":"t2"}}}',
        encoding="utf-8",
    )
    return ext


def _sample_opp(net_bps: float, est_profit: float = 1.5) -> dict:
    return {
        "symbol": "DOGE",
        "net_bps": net_bps,
        "est_profit_usd": est_profit,
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "buy_ask": 0.15,
        "notional_usd": 75.0,
    }


def test_run_extended_profit_tick_runs_strategies(ext_env):
    ext = ext_env
    res = ext.run_extended_profit_tick(profile="standard")
    assert res["success"] is True
    assert res["strategy_count"] == 2
    assert "stablecoin_peg" in res["results"]
    assert "triangular_paper" in res["results"]


def test_stablecoin_peg_books_on_deviation(ext_env, monkeypatch):
    ext = ext_env
    from backend.services import crypto_exchange_service as ex

    monkeypatch.setattr(ex, "_price_usd", lambda sym: 0.995 if sym == "USDT" else 1.005)
    res = ext.tick_stablecoin_peg({"min_deviation_bps": 5, "notional_usd": 100, "agent_id": "peg_test"})
    assert res["executed"] is True
    assert res["est_profit_usd"] > 0


def test_fast_arb_rescan_ready_when_above_threshold(ext_env, monkeypatch):
    ext = ext_env
    opp = _sample_opp(18.0)

    monkeypatch.setattr(
        "backend.services.exchange_arbitrage_service.scan_opportunities",
        lambda **kw: {"opportunity_count": 1, "opportunities": [opp]},
    )
    res = ext.tick_fast_arb_rescan({"min_net_bps": 12, "notional_usd": 75, "execute_on_threshold": False})
    assert res["ready"] is True
    assert res["top_net_bps"] == 18.0
    state = ext.read_arb_threshold_state()
    assert state["ready"] is True
    assert state["best_net_bps"] == 18.0
    assert state["threshold_bps"] == 12


def test_fast_arb_rescan_not_ready_below_threshold(ext_env, monkeypatch):
    ext = ext_env
    opp = _sample_opp(5.7)

    monkeypatch.setattr(
        "backend.services.exchange_arbitrage_service.scan_opportunities",
        lambda **kw: {"opportunity_count": 1, "opportunities": [opp]},
    )
    res = ext.tick_fast_arb_rescan({"min_net_bps": 12, "notional_usd": 75, "execute_on_threshold": True})
    assert res["ready"] is False
    assert res["executed"] is False
    state = ext.read_arb_threshold_state()
    assert state["ready"] is False
    assert state["best_net_bps"] == 5.7


def test_fast_arb_rescan_executes_on_threshold(ext_env, monkeypatch):
    ext = ext_env
    opp = _sample_opp(20.0)
    calls = {"exec": 0}

    monkeypatch.setattr(
        "backend.services.exchange_arbitrage_service.scan_opportunities",
        lambda **kw: {"opportunity_count": 1, "opportunities": [opp]},
    )
    monkeypatch.setattr(
        "backend.services.exchange_arbitrage_service.live_enabled",
        lambda: False,
    )

    def fake_exec(opp_in, agent_id=None, dry_run=False):
        calls["exec"] += 1
        return {"success": True, "mode": "paper"}

    def fake_book(agent_id, opp_in, exec_res):
        return {}

    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.execute_spatial_arbitrage",
        fake_exec,
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.book_agent_profit",
        fake_book,
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_scan",
        lambda **kw: "path-1",
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.record_execution",
        lambda **kw: None,
    )

    res = ext.tick_fast_arb_rescan({
        "min_net_bps": 12,
        "notional_usd": 75,
        "execute_on_threshold": True,
        "agent_id": "arb_live_dual_farm",
        "max_executions_per_tick": 1,
    })
    assert res["ready"] is True
    assert res["executed"] is True
    assert calls["exec"] == 1


def test_defi_rotation_sets_executed(ext_env, monkeypatch):
    ext = ext_env
    from backend.services import crypto_exchange_service as ex

    monkeypatch.setattr(ex, "_price_in_quote", lambda sym, q: 1.0)
    monkeypatch.setattr(ex, "get_wallet", lambda uid: {"assets": {"LINK": 100.0}})
    monkeypatch.setattr(
        ex,
        "execute_swap",
        lambda uid, tid, sym, side, amt, q: {"success": True, "trade": {"id": "t1"}},
    )
    res = ext.tick_defi_rotation({
        "assets": ["LINK"],
        "trade_mn2": 1.5,
        "treasury_user_id": "platform_treasury",
    })
    assert res["executed"] is True
    assert res["success"] is True
