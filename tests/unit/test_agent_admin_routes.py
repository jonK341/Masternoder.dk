"""Agents control board HTTP routes."""
from flask import Flask


def _app(monkeypatch):
    monkeypatch.delenv("MN2_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    from backend.routes.agent_admin_routes import agent_admin_bp
    app = Flask(__name__)
    app.register_blueprint(agent_admin_bp)
    return app


def test_control_status_ok(monkeypatch):
    monkeypatch.setattr(
        "backend.services.agent_admin_service.get_control_status",
        lambda: {
            "success": True,
            "strategies": ["market_maker"],
            "live_distribute": False,
        },
    )
    c = _app(monkeypatch).test_client()
    r = c.get("/api/agents/control/status", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    assert r.get_json().get("success") is True


def test_control_fund_dry_run(monkeypatch):
    seen = {}

    def _fake_distribute(*, dry_run=None, allow_live=False):
        seen["dry_run"] = dry_run
        return {"success": True, "dry_run": True, "results": []}

    monkeypatch.setattr(
        "backend.services.agent_wallet_service.distribute_agent_funding",
        _fake_distribute,
    )
    c = _app(monkeypatch).test_client()
    r = c.post(
        "/api/agents/control/fund",
        json={},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert r.status_code == 200
    assert r.get_json().get("dry_run") is True


def test_control_trader_run(monkeypatch):
    monkeypatch.setattr(
        "backend.services.agent_trader_service.run_all_traders",
        lambda: {"success": True, "trades": 2, "agents": 2},
    )
    c = _app(monkeypatch).test_client()
    r = c.post(
        "/api/agents/control/trader/run",
        json={},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert r.status_code == 200
    assert r.get_json().get("trades") == 2


def test_control_halt_resume(monkeypatch):
    calls = []

    def _set_switch(**kwargs):
        calls.append(kwargs)
        return {"success": True, "global_halt": bool(kwargs.get("global_halt"))}

    monkeypatch.setattr("backend.services.agent_kill_switch.set_switch", _set_switch)
    monkeypatch.setattr(
        "backend.services.admin_audit_service.log_action",
        lambda *a, **k: None,
    )
    c = _app(monkeypatch).test_client()
    h = c.post(
        "/api/agents/control/halt",
        json={"reason": "test"},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert h.status_code == 200
    assert h.get_json().get("global_halt") is True
    r = c.post(
        "/api/agents/control/resume",
        json={},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert r.status_code == 200
    assert calls and calls[0].get("global_halt") is True
    assert calls[-1].get("global_halt") is False
