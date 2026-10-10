"""Per-user exchange daemon config, venue farming, and daemon rentals."""
import pytest


@pytest.fixture
def daemon_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import agent_marketplace_service as mkt
    from backend.services import exchange_rental_service as rent
    from backend.services import exchange_user_daemon_service as daemon

    data = tmp_path / "crypto_exchange"
    (data / "user_agents").mkdir(parents=True)
    (data / "user_daemons").mkdir(parents=True)

    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(mkt, "_USER_AGENTS_DIR", str(data / "user_agents"))
    monkeypatch.setattr(rent, "_RENTALS_PATH", str(data / "rental_history.jsonl"))
    monkeypatch.setattr(daemon, "_CONFIG_DIR", str(data / "user_daemons"))

    bal = {"u1": 5000.0}
    monkeypatch.setattr(ex, "_get_quote_balance", lambda uid, q: float(bal.get(uid, 0.0)))
    monkeypatch.setattr(ex, "_adjust_quote_balance",
                        lambda uid, q, delta, source, meta=None: bal.__setitem__(uid, bal.get(uid, 0.0) + float(delta)))

    try:
        from backend.services import exchange_trust_service as trust
        monkeypatch.setattr(trust, "_POLICY_PATH", str(data / "trust_policy.json"))
        ex._write_json(str(data / "trust_policy.json"), {"require_manual_activation": False, "suspended_users": []})
        monkeypatch.setattr(trust, "check_activation", lambda *a, **k: {"allowed": True})
    except Exception:
        pass

    return {"ex": ex, "mkt": mkt, "rent": rent, "daemon": daemon, "bal": bal}


def test_rent_daemon_sets_farm_fields(daemon_env):
    rent = daemon_env["rent"]
    r = rent.rent_agent("u1", "rent_daemon_cross_7d")
    assert r["success"] is True
    agent = r["agent"]
    assert agent["is_daemon"] is True
    assert "binance" in agent["farm_venues"]
    assert "BTC" in agent["farm_symbols"]
    assert agent["farm_strategy"] == "cross_exchange_farm"


def test_save_and_load_daemon_config(daemon_env):
    daemon = daemon_env["daemon"]
    saved = daemon.save_config("u1", {
        "strategy": "ai_multi_venue",
        "venues": ["binance", "nonkyc", "mexc"],
        "symbols": ["BTC", "ETH"],
        "notional_usd": 500,
    })
    assert saved["success"] is True
    cfg = daemon.get_config("u1")
    assert cfg["success"] is True
    assert cfg["config"]["strategy"] == "ai_multi_venue"
    assert cfg["config"]["venues"] == ["binance", "nonkyc", "mexc"]
    assert cfg["available_venues"]
    assert "mexc" in {v["id"] for v in cfg["available_venues"]}


def test_run_user_daemon_with_spread_bonus(daemon_env, monkeypatch):
    rent = daemon_env["rent"]
    daemon = daemon_env["daemon"]
    mkt = daemon_env["mkt"]

    r = rent.rent_agent("u1", "rent_daemon_cross_7d")
    aid = r["agent"]["agent_id"]
    data = mkt._read_user_agents("u1")
    data["agents"][aid]["farm_venues"] = ["binance", "coinbase"]
    data["agents"][aid]["farm_symbols"] = ["BTC"]
    mkt._write_user_agents("u1", data)

    from backend.services import exchange_arbitrage_service as arb
    original_scan = arb.scan_opportunities

    def fake_scan(symbols=None, venues=None, *, injected=None, notional_usd=None):
        return original_scan(symbols, venues, notional_usd=notional_usd, injected=injected or {
            "binance": {"BTC": {"bid": 99.9, "ask": 100.0, "last": 100.0}},
            "coinbase": {"BTC": {"bid": 108.0, "ask": 108.1, "last": 108.0}},
        })

    monkeypatch.setattr(arb, "scan_opportunities", fake_scan)

    daemon.save_config("u1", {"agent_ids": [aid], "venues": ["binance", "coinbase"], "symbols": ["BTC"]})
    out = daemon.run_user_daemon("u1")
    assert out["success"] is True
    assert out["ran"] == 1
    data = mkt._read_user_agents("u1")
    ag = data["agents"][aid]
    assert float(ag.get("realized_profit_usd") or 0) > 0
    assert (ag.get("last_action") or {}).get("venue_farm_bonus_usd", 0) > 0
