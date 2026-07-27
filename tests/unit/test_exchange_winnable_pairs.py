"""Winnable pairs supervisor — search + execute on ranked routes."""
import pytest


@pytest.fixture
def winnable_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import exchange_profit_pair_search_service as pps
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import exchange_winnable_pairs_service as win

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    ppp_path = data / "profit_path_protocol.json"
    ppp_path.write_text(
        '{"winnable_pairs_supervisor":{"enabled":true,"min_net_bps":10,"min_search_score":15,'
        '"max_executions_per_tick":2,"notional_usd":50,"agent_id":"arb_winnable_pairs"},'
        '"profit_pair_search":{"enabled":true}}',
        encoding="utf-8",
    )

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ppp, "_CFG_PATH", str(ppp_path))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(pps, "_INDEX_PATH", str(data / "profit_pair_search_index.json"))
    monkeypatch.setattr(win, "enabled", lambda: True)
    return {"win": win, "arb": arb, "pps": pps}


def test_filter_winnable_respects_thresholds(winnable_env):
    win = winnable_env["win"]
    hits = [
        {"symbol": "DOGE", "buy_venue": "binance", "sell_venue": "nonkyc", "avg_net_bps": 20, "search_score": 30},
        {"symbol": "BTC", "buy_venue": "binance", "sell_venue": "nonkyc", "avg_net_bps": 5, "search_score": 40},
    ]
    out = win._filter_winnable(hits, min_bps=10, min_score=15)
    assert len(out) == 1
    assert out[0]["symbol"] == "DOGE"


def test_run_winnable_pairs_executes_top_route(winnable_env, monkeypatch):
    win = winnable_env["win"]
    search = {
        "success": True,
        "hot_symbols": ["DOGE"],
        "hits": [{
            "symbol": "DOGE",
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "avg_net_bps": 25,
            "search_score": 40,
        }],
    }
    monkeypatch.setattr(
        winnable_env["arb"],
        "scan_opportunities",
        lambda **kw: {
            "success": True,
            "opportunities": [{
                "symbol": "DOGE",
                "buy_venue": "binance",
                "sell_venue": "nonkyc",
                "net_bps": 25,
                "notional_usd": 50,
                "est_profit_usd": 0.12,
            }],
        },
    )
    monkeypatch.setattr(winnable_env["arb"], "live_enabled", lambda: False)
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.execute_spatial_arbitrage",
        lambda opp, agent_id=None, dry_run=None: {"success": True, "mode": "paper"},
    )
    monkeypatch.setattr(
        "backend.services.exchange_live_execution_service.book_agent_profit",
        lambda *a, **k: {"agent_id": "arb_winnable_pairs", "last_action": {"executed": True}},
    )
    monkeypatch.setattr(
        "backend.services.exchange_extended_profit_service.write_arb_threshold_state",
        lambda **kw: {},
    )

    res = win.run_winnable_pairs_tick(pair_search=search)
    assert res["success"] is True
    assert res["winnable_count"] == 1
    assert res["executed_count"] == 1
    assert res["executions"][0]["success"] is True
