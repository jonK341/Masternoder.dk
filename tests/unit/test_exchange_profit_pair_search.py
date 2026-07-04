"""Profit Pair Search — ranking, ledger query, catalog intersection."""
import os
import pytest


@pytest.fixture
def pps_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import exchange_profit_pair_search_service as pps
    from backend.services import external_exchange_connector_service as conn

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)

    cfg_path = data / "profit_path_protocol.json"
    ledger_path = data / "profit_path_ledger.jsonl"
    index_path = data / "profit_pair_search_index.json"
    catalog_path = data / "profit_pair_catalog_cache.json"

    monkeypatch.setattr(ppp, "_CFG_PATH", str(cfg_path))
    monkeypatch.setattr(ppp, "_LEDGER_PATH", str(ledger_path))
    monkeypatch.setattr(pps, "_INDEX_PATH", str(index_path))
    monkeypatch.setattr(pps, "_CATALOG_CACHE_PATH", str(catalog_path))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(conn, "_PRICE_CACHE_PATH", str(data / "external_prices.json"))

    monkeypatch.setenv("EXCHANGE_PROFIT_PAIR_SEARCH", "1")
    ex._write_json(str(cfg_path), {
        "enabled": True,
        "profit_pair_search": {
            "enabled": True,
            "top_n": 5,
            "ledger_lookback_hours": 24,
            "catalog_venues": ["binance", "nonkyc"],
            "skip_agent_symbols_when_hot": True,
            "min_live_net_bps": 5,
        },
    })

    return {"pps": pps, "ppp": ppp, "conn": conn}


def test_ledger_ranked_routes_prefers_fills(pps_env):
    ppp = pps_env["ppp"]
    pps = pps_env["pps"]

    for sym, fills in (("DOGE", 2), ("BTC", 0)):
        opp = {
            "symbol": sym,
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "gross_bps": 40.0,
            "fee_bps": 10.0,
            "net_bps": 30.0,
            "notional_usd": 25.0,
        }
        pid = ppp.record_scan(agent_id="arb_test", best=opp, decision="attempt", mode="paper")
        for _ in range(fills):
            ppp.record_execution(
                path_id=pid,
                agent_id="arb_test",
                opp=opp,
                exec_res={"success": True, "mode": "paper", "est_profit_usd": 0.5},
            )

    rows = pps.ledger_ranked_routes(min_attempts=1, limit=10)
    assert rows
    assert rows[0]["symbol"] == "DOGE"
    assert rows[0]["fill_count"] == 2
    assert rows[0]["avg_net_bps"] == 30.0


def test_catalog_intersection_uses_cache(pps_env, monkeypatch):
    pps = pps_env["pps"]

    monkeypatch.setattr(pps, "_fetch_binance_usdc_bases", lambda: {"BTC", "ETH", "DOGE"})
    monkeypatch.setattr(pps, "_fetch_nonkyc_usdt_bases", lambda: {"BTC", "DOGE", "XRP"})

    common = pps.catalog_intersection(["binance", "nonkyc"])
    assert common == ["BTC", "DOGE"]


def test_merge_rankings_combines_ledger_and_live(pps_env):
    pps = pps_env["pps"]

    ledger = [{
        "symbol": "DOGE",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "avg_net_bps": 28.0,
        "hit_rate_pct": 50.0,
        "fill_count": 2,
        "last_profit_usd": 1.2,
    }]
    live = [{
        "symbol": "DOGE",
        "buy_venue": "binance",
        "sell_venue": "nonkyc",
        "live_score": 35.0,
        "est_profit_usd": 0.8,
    }]
    merged = pps._merge_rankings(ledger, live, top_n=3)
    assert len(merged) == 1
    assert merged[0]["symbol"] == "DOGE"
    assert merged[0]["search_score"] > 0
    assert "ledger" in merged[0]["sources"] or "live" in merged[0]["sources"]


def test_run_search_updates_index(pps_env, monkeypatch):
    pps = pps_env["pps"]
    from backend.services import exchange_arbitrage_service as arb

    monkeypatch.setattr(pps, "catalog_intersection", lambda venues=None: ["BTC", "DOGE"])
    monkeypatch.setattr(
        pps,
        "ledger_ranked_routes",
        lambda **kw: [{
            "symbol": "DOGE",
            "buy_venue": "binance",
            "sell_venue": "nonkyc",
            "avg_net_bps": 25.0,
            "hit_rate_pct": 100.0,
            "fill_count": 1,
            "last_profit_usd": 0.5,
            "source": "ledger",
        }],
    )

    injected = {
        "binance": {"DOGE": {"bid": 0.09, "ask": 0.10, "last": 0.10}},
        "nonkyc": {"DOGE": {"bid": 0.11, "ask": 0.12, "last": 0.11}},
    }
    monkeypatch.setattr(
        arb,
        "scan_opportunities",
        lambda symbols=None, venues=None, injected=None, notional_usd=None: {
            "success": True,
            "opportunities": [{
                "symbol": "DOGE",
                "buy_venue": "binance",
                "sell_venue": "nonkyc",
                "net_bps": 40.0,
                "est_profit_usd": 0.9,
            }],
        },
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_pair_search_service.vapi.venue_execution_eligible",
        lambda vid: str(vid).lower() in ("binance", "nonkyc"),
    )

    res = pps.run_profit_pair_search(injected=injected)
    assert res["success"] is True
    assert "DOGE" in res["hot_symbols"]
    idx = pps.read_index()
    assert idx.get("hits")
    assert idx["hits"][0]["symbol"] == "DOGE"


def test_resolve_agent_symbols_overrides_when_hot(pps_env):
    pps = pps_env["pps"]
    pps._write_index({"hits": [{"symbol": "XRP"}, {"symbol": "DOGE"}]})

    resolved = pps.resolve_agent_symbols(["BTC", "ETH"], hot_symbols=["DOGE", "SOL"])
    assert resolved == ["DOGE", "SOL"]


def test_resolve_agent_symbols_keeps_agent_list_when_disabled(pps_env, monkeypatch):
    pps = pps_env["pps"]
    ppp = pps_env["ppp"]
    monkeypatch.delenv("EXCHANGE_PROFIT_PAIR_SEARCH", raising=False)
    from backend.services import crypto_exchange_service as ex
    cfg = ppp.load_config()
    cfg["profit_pair_search"] = {"enabled": False}
    ex._write_json(ppp._CFG_PATH, cfg)

    resolved = pps.resolve_agent_symbols(["BTC", "ETH"])
    assert resolved == ["BTC", "ETH"]


def test_execution_hits_exclude_scan_only_venues(pps_env, monkeypatch):
    pps = pps_env["pps"]

    monkeypatch.setattr(
        pps,
        "_merge_rankings",
        lambda ledger_rows, live_rows, top_n=12: [
            {
                "symbol": "ADA",
                "buy_venue": "bingx",
                "sell_venue": "okx",
                "search_score": 40.0,
                "sources": ["live"],
            },
            {
                "symbol": "DOGE",
                "buy_venue": "binance",
                "sell_venue": "nonkyc",
                "search_score": 35.0,
                "sources": ["ledger", "live"],
            },
        ],
    )
    monkeypatch.setattr(
        "backend.services.exchange_profit_pair_search_service.vapi.venue_execution_eligible",
        lambda vid: str(vid).lower() in ("binance", "nonkyc"),
    )
    monkeypatch.setattr(pps, "catalog_intersection", lambda venues=None: ["DOGE", "ADA"])
    monkeypatch.setattr(pps, "ledger_ranked_routes", lambda **kw: [])
    monkeypatch.setattr(pps, "live_spread_rank", lambda *a, **k: [])

    res = pps.run_profit_pair_search()
    assert res["success"] is True
    assert "DOGE" in res["hot_symbols"]
    assert "ADA" not in res["hot_symbols"]
    assert all(h["buy_venue"] != "bingx" for h in res["hits"])
