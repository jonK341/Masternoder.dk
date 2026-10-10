"""Trust system, activations, composite intelligence, and Live Watch."""
import pytest


@pytest.fixture
def trust_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import agent_marketplace_service as mkt
    from backend.services import exchange_leveling_service as lvl
    from backend.services import exchange_trust_service as trust

    data = tmp_path / "crypto_exchange"
    (data / "user_agents").mkdir(parents=True)
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(mkt, "_USER_AGENTS_DIR", str(data / "user_agents"))
    monkeypatch.setattr(mkt, "_SALES_PATH", str(data / "agent_sales.jsonl"))
    monkeypatch.setattr(lvl, "_STATE_DIR", str(data / "exchange_leveling"))
    monkeypatch.setattr(trust, "_STATE_DIR", str(data / "exchange_trust"))
    monkeypatch.setattr(trust, "_POLICY_PATH", str(data / "exchange_trust_policy.json"))
    ex._write_json(str(data / "exchange_trust_policy.json"), {
        "min_user_trust_floor": 0, "require_manual_activation": False, "suspended_users": [],
    })

    bal = {"u1": 50000.0}
    monkeypatch.setattr(ex, "_get_quote_balance", lambda uid, q: float(bal.get(uid, 0.0)))
    monkeypatch.setattr(ex, "_adjust_quote_balance",
                        lambda uid, q, delta, source, meta=None: bal.__setitem__(uid, bal.get(uid, 0.0) + float(delta)))
    return {"ex": ex, "mkt": mkt, "trust": trust}


def test_user_trust_tier_and_profile(trust_env):
    trust = trust_env["trust"]
    p = trust.user_trust_profile("u1")
    assert p["success"] is True
    assert p["trust_score"] >= 15
    assert p["tier"]["name"] in ("Unverified", "Bronze", "Silver", "Gold", "Platinum")
    assert len(p["activations"]) >= 4


def test_agent_activation_gate(trust_env):
    trust = trust_env["trust"]
    mkt = trust_env["mkt"]
    # Manual activation required for this test
    trust.owner_set_policy(require_manual_activation=True)
    buy = mkt.purchase_agent("u1", "tmpl_starter_spatial")
    aid = buy["agent"]["agent_id"]
    agent = mkt._read_user_agents("u1")["agents"][aid]
    assert agent.get("activation") == "pending"
    tick_blocked = mkt.run_user_agent_tick("u1", aid)
    assert tick_blocked["success"] is False
    act = trust.set_agent_activation("u1", aid, "active")
    assert act["success"] is True
    tick_ok = mkt.run_user_agent_tick("u1", aid)
    assert tick_ok["success"] is True
    assert tick_ok.get("trust_score") is not None
    assert tick_ok.get("composite_iq") is not None


def test_composite_intelligence_grows_with_trust(trust_env):
    trust = trust_env["trust"]
    agent = {"intelligence": 120, "realized_profit_usd": 50, "trade_count": 10,
             "game_time_sec": 7200, "mastery_pct": 30, "activation": "active"}
    low = trust.composite_intelligence(20, agent)
    high = trust.composite_intelligence(80, agent)
    assert high["composite_iq"] > low["composite_iq"]
    assert high["trust_edge_bps"] >= low["trust_edge_bps"]


def test_user_live_watch(trust_env):
    from backend.services.exchange_live_watch_service import user_live_watch
    mkt = trust_env["mkt"]
    buy = mkt.purchase_agent("u1", "tmpl_pro_triangular")
    mkt.run_user_agent_tick("u1", buy["agent"]["agent_id"])
    w = user_live_watch("u1")
    assert w["success"] is True
    assert w["trust"]["trust_score"] > 0
    assert len(w["agents"]) == 1
    assert "feed" in w


def test_owner_policy_suspend(trust_env):
    trust = trust_env["trust"]
    trust.owner_set_policy(suspend_user="bad_u")
    chk = trust.check_activation("bad_u", "run_bots")
    assert chk["allowed"] is False
    assert chk["error"] == "user_suspended"
    trust.owner_set_policy(unsuspend_user="bad_u")
    assert "bad_u" not in (trust._policy().get("suspended_users") or [])
