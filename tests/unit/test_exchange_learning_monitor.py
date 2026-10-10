"""Super skills, adaptive learning, and the unified live trading monitor."""
import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import agent_marketplace_service as mkt
    from backend.services import exchange_leveling_service as lvl

    data = tmp_path / "crypto_exchange"
    (data / "user_agents").mkdir(parents=True)
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(ex, "_TREASURY_PATH", str(data / "fee_treasury.json"))
    monkeypatch.setattr(mkt, "_USER_AGENTS_DIR", str(data / "user_agents"))
    monkeypatch.setattr(mkt, "_SALES_PATH", str(data / "agent_sales.jsonl"))
    monkeypatch.setattr(lvl, "_STATE_DIR", str(data / "exchange_leveling"))
    try:
        from backend.services import exchange_trust_service as trust
        monkeypatch.setattr(trust, "_POLICY_PATH", str(data / "exchange_trust_policy.json"))
        ex._write_json(str(data / "exchange_trust_policy.json"), {
            "require_manual_activation": False, "min_user_trust_floor": 0, "suspended_users": [],
        })
        monkeypatch.setattr(trust, "check_activation", lambda *a, **k: {"allowed": True})
    except Exception:
        pass

    bal = {"u1": 50000.0}
    monkeypatch.setattr(ex, "_get_quote_balance", lambda uid, q: float(bal.get(uid, 0.0)))
    monkeypatch.setattr(ex, "_adjust_quote_balance",
                        lambda uid, q, delta, source, meta=None: bal.__setitem__(uid, bal.get(uid, 0.0) + float(delta)))
    return {"ex": ex, "mkt": mkt, "bal": bal}


def test_super_skills_present_in_catalog():
    from backend.services import exchange_bot_skills_service as sk
    skills = {s["id"]: s for s in sk.load_skills()}
    for sid in ("statistical_arbitrage", "market_making_as", "sentiment_alpha",
                "latency_momentum", "ml_price_forecast", "kelly_sizing"):
        assert sid in skills, sid
        assert skills[sid].get("super") is True


def test_learning_increases_proficiency_and_intelligence():
    from backend.services import exchange_agent_learning_service as learn
    agent = {"capital_usd": 1000, "skills": ["statistical_arbitrage", "kelly_sizing"], "skill_proficiency": {}}
    assert learn.learning_edge_bonus_bps(agent) == 0.0
    base_iq = learn.agent_intelligence(agent)
    for _ in range(20):
        learn.learn_from_profit(agent, 5.0)
    assert agent["skill_proficiency"]["statistical_arbitrage"] > 0
    assert learn.learning_edge_bonus_bps(agent) > 0
    assert learn.agent_intelligence(agent) > base_iq
    # Super skills learn faster than a non-super skill given identical rewards.
    a2 = {"capital_usd": 1000, "skills": ["statistical_arbitrage", "spatial_arbitrage"], "skill_proficiency": {}}
    for _ in range(5):
        learn.learn_from_profit(a2, 5.0)
    assert a2["skill_proficiency"]["statistical_arbitrage"] > a2["skill_proficiency"]["spatial_arbitrage"]


def test_agent_gets_smarter_across_ticks(env):
    mkt = env["mkt"]
    buy = mkt.purchase_agent("u1", "tmpl_sentient_apex")
    assert buy["success"] is True, buy.get("error")
    agent_id = buy["agent"]["agent_id"]
    first = mkt.run_user_agent_tick("u1", agent_id, volatility=0.5)
    for _ in range(15):
        last = mkt.run_user_agent_tick("u1", agent_id, volatility=0.5)
    assert last["intelligence"] > first["intelligence"]
    assert last["mastery_pct"] > 0
    assert last["action"]["learning_bonus_bps"] >= first["action"]["learning_bonus_bps"]


def test_live_monitor_aggregates_bots_and_feed(env):
    from backend.services.exchange_trading_monitor_service import live_monitor
    mkt = env["mkt"]
    buy = mkt.purchase_agent("u1", "tmpl_pro_triangular")
    mkt.run_user_agent_tick("u1", buy["agent"]["agent_id"], volatility=0.4)

    mon = live_monitor("u1")
    assert mon["success"] is True
    assert mon["totals"]["bot_count"] == 1
    assert mon["totals"]["avg_intelligence"] >= 100
    assert len(mon["bots"]) == 1
    kinds = {f["kind"] for f in mon["feed"]}
    assert "bot_profit" in kinds or "purchase" in kinds
    assert all("ts" in f for f in mon["feed"])
