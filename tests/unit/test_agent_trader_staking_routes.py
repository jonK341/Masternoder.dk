"""Trader staking HTTP routes."""
from flask import Flask


def _app():
    from backend.routes.agent_trader_staking_routes import agent_trader_staking_bp
    app = Flask(__name__)
    app.register_blueprint(agent_trader_staking_bp)
    return app


def test_trader_staking_status_ok(monkeypatch):
    monkeypatch.setattr(
        "backend.services.agent_trader_staking_service.list_trader_agents_status",
        lambda follower_user_id=None: {
            "success": True,
            "trader_agents": [],
            "pool_staked_by_traders_mn2": 0,
            "follower": {"following": False},
        },
    )
    c = _app().test_client()
    r = c.get("/api/agents/trader-staking/status?user_id=default_user")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True


def test_trader_staking_status_passes_query_user(monkeypatch):
    seen = {}

    def _fake_list(**kwargs):
        seen.update(kwargs)
        return {"success": True, "trader_agents": [], "follower": {"following": False}}

    monkeypatch.setattr(
        "backend.services.agent_trader_staking_service.list_trader_agents_status",
        _fake_list,
    )
    c = _app().test_client()
    r = c.get("/api/agents/trader-staking/status?user_id=player_42")
    assert r.status_code == 200
    assert seen.get("follower_user_id") == "player_42"
