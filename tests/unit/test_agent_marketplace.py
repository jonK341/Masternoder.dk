"""Bot skills, cross-trade profit calculator, and agent marketplace tests."""
import pytest


@pytest.fixture
def market_env(tmp_path, monkeypatch):
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

    # Stub MN2 balance so purchases don't touch real points DB.
    bal = {"u_buyer": 5000.0}
    monkeypatch.setattr(ex, "_get_quote_balance", lambda uid, q: float(bal.get(uid, 0.0)))

    def _adjust(uid, q, delta, source, meta):
        bal[uid] = bal.get(uid, 0.0) + float(delta)

    monkeypatch.setattr(ex, "_adjust_quote_balance", _adjust)
    return {"ex": ex, "mkt": mkt, "bal": bal}


def test_skill_catalog_includes_named_sets():
    from backend.services import exchange_bot_skills_service as sk
    skills = sk.list_skills()
    assert skills["success"] is True
    assert skills["skill_set_count"] >= 8
    assert any(s["id"] == "starter_arbitrage" for s in skills["skill_sets"])


def test_skill_catalog_and_blended_edge():
    from backend.services import exchange_bot_skills_service as sk
    skills = sk.list_skills()
    assert skills["success"] is True
    assert skills["skill_count"] >= 12
    blended = sk.blended_edge_bps(["spatial_arbitrage", "triangular_arbitrage"], 0.5)
    assert blended["blended_edge_bps"] > 0
    # Diminishing returns: blended < naive sum of the two edges.
    naive = sum(sk.estimate_skill_edge(s, 0.5) for s in ["spatial_arbitrage", "triangular_arbitrage"])
    assert blended["blended_edge_bps"] < naive


def test_cross_trade_projection_scales_with_capital():
    from backend.services import exchange_profit_calculator_service as calc
    small = calc.cross_trade_projection(500, ["spatial_arbitrage"], cycles_per_day=24)
    big = calc.cross_trade_projection(5000, ["spatial_arbitrage"], cycles_per_day=24)
    assert big["daily_profit_usd"] > small["daily_profit_usd"]
    assert small["blended_edge_bps"] > 0
    assert small["monthly_profit_usd"] == pytest.approx(small["daily_profit_usd"] * 30, rel=1e-6)


def test_net_margin_bps_accounts_for_fees():
    from backend.services import exchange_profit_calculator_service as calc
    m = calc.net_margin_bps(100.0, 105.0, buy_fee_bps=10, sell_fee_bps=60, transfer_bps=20, slippage_bps=5)
    assert m["gross_bps"] == pytest.approx(500.0, rel=1e-3)
    assert m["net_bps"] == pytest.approx(500.0 - 95.0, rel=1e-3)
    assert m["profitable"] is True


def test_catalog_includes_skill_sets(market_env):
    mkt = market_env["mkt"]
    cat = mkt.get_catalog()
    assert cat["success"] is True
    tmpl = cat["templates"][0]
    assert tmpl.get("skill_set", {}).get("name")
    assert len(tmpl.get("skill_details") or []) >= 2
    assert tmpl.get("blended_edge_bps", 0) > 0


def test_purchase_generates_user_agent_and_charges_mn2(market_env):
    mkt = market_env["mkt"]
    res = mkt.purchase_agent("u_buyer", "tmpl_starter_spatial")
    assert res["success"] is True, res.get("error")
    assert res["spent_mn2"] == 250
    # 5000 - 250 spent, plus a small first-agent achievement MN2 reward.
    assert market_env["bal"]["u_buyer"] == pytest.approx(4750.0, abs=0.5)
    agents = mkt.list_user_agents("u_buyer")
    assert agents["agent_count"] == 1
    assert agents["agents"][0]["skills"]


def test_purchase_rejects_insufficient_mn2(market_env):
    mkt = market_env["mkt"]
    market_env["bal"]["u_buyer"] = 10.0
    res = mkt.purchase_agent("u_buyer", "tmpl_quant_multi")
    assert res["success"] is False
    assert res["error"] == "insufficient_mn2"


def test_run_agent_accrues_profit_to_own_account(market_env):
    mkt = market_env["mkt"]
    buy = mkt.purchase_agent("u_buyer", "tmpl_pro_triangular")
    agent_id = buy["agent"]["agent_id"]
    tick = mkt.run_user_agent_tick("u_buyer", agent_id, volatility=0.4)
    assert tick["success"] is True
    assert tick["realized_profit_usd"] > 0
    assert tick["game_time_sec"] >= 3600
    assert tick["agent_level"] >= 1
    portfolio = mkt.user_portfolio("u_buyer")
    assert portfolio["total_realized_profit_usd"] > 0
    assert portfolio["projection"]["combined_daily_profit_usd"] > 0


def test_sales_summary_tracks_revenue(market_env):
    mkt = market_env["mkt"]
    mkt.purchase_agent("u_buyer", "tmpl_starter_spatial")
    summary = mkt.sales_summary()
    assert summary["sales_count"] == 1
    assert summary["revenue_mn2"] == 250
