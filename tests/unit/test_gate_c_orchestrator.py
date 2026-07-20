"""Gate C orchestrator tests — Stage 2 market + trader agents."""
import pytest


def test_gate_c_status_service():
    from backend.services.gate_c_status_service import check_gate_c
    r = check_gate_c()
    assert r.get("success") is True
    assert r.get("gate") == "C"
    assert isinstance(r.get("checks"), list)
    assert len(r["checks"]) >= 7


def test_maybe_distribute_treasury_after_deposit(monkeypatch):
    from backend.services.mn2_deposit_scanner import maybe_distribute_treasury_after_deposit

    called = {}

    def _fake():
        called["yes"] = True
        return {"success": True, "results": []}

    monkeypatch.setattr(
        "backend.services.agent_wallet_service.distribute_agent_funding",
        _fake,
    )
    r = maybe_distribute_treasury_after_deposit()
    assert called.get("yes") is True
    assert r.get("success") is True


def test_copy_trading_follow_unfollow(tmp_path, monkeypatch):
    from backend.services import mn2_copy_trading as ct

    follows = tmp_path / "follows.json"
    monkeypatch.setattr(ct, "_FOLLOWS", str(follows))
    monkeypatch.setattr(ct, "_LOG", str(tmp_path / "log.jsonl"))

    r1 = ct.upsert_follower("user_a", "trader_agent_1", scale=0.5, max_mn2_per_step=10)
    assert r1.get("success") is True

    r2 = ct.remove_follower("user_a")
    assert r2.get("success") is True
    assert r2.get("removed") is True

    data = ct._load()
    assert "user_a" not in (data.get("followers") or {})


def test_copy_trading_follow_route(monkeypatch):
    from backend.routes.agent_trader_staking_routes import agent_trader_staking_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(agent_trader_staking_bp)
    monkeypatch.setattr(
        "backend.services.mn2_copy_trading.upsert_follower",
        lambda uid, lid, **kw: {"success": True, "follower": {"follower_user_id": uid, "leader_agent_id": lid}},
    )
    c = app.test_client()
    r = c.post(
        "/api/mn2/copy-trading/follow",
        json={"user_id": "player_1", "leader_agent_id": "trader_agent_2", "scale": 0.25},
    )
    assert r.status_code == 200
    assert r.get_json().get("success") is True


def test_gate_c_health_route():
    from backend.routes.health_routes import health_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(health_bp)
    c = app.test_client()
    r = c.get("/api/health/gate-c")
    assert r.status_code in (200, 503)
    data = r.get_json()
    assert data.get("gate") == "C"
    assert "ready_for_stage_3" in data
