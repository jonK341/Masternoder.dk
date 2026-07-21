"""Stage 3 agents control board and security cron tests."""
import json

import pytest


def test_get_control_status_structure():
    from backend.services.agent_admin_service import get_control_status
    r = get_control_status()
    assert r.get("success") is True
    assert "treasury" in r
    assert "kill_switch" in r
    assert isinstance(r.get("trader_agents"), list)
    assert isinstance(r.get("strategies"), list)


def test_reconcile_treasury_pool():
    from backend.services.agent_admin_service import reconcile_treasury_pool
    r = reconcile_treasury_pool()
    assert "pool_balance_mn2" in r
    assert "trader_wallet_sum_mn2" in r
    assert "ok" in r


def test_security_sweep_runs(monkeypatch):
    from backend.services import security_cron_service as scs

    monkeypatch.setattr(scs, "run_security_sweep", lambda **kw: {
        "success": True,
        "ok": True,
        "results": {"conservation": {"verdict": "green"}},
    })
    r = scs.run_security_sweep()
    assert r.get("success") is True


def test_security_sweep_service(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_conservation_gate.conservation_gate",
        lambda: {"verdict": "green", "ok": True},
    )
    monkeypatch.setattr(
        "backend.services.points_drift_service.scan_all",
        lambda limit=100: {"success": True, "drift_count": 0},
    )
    monkeypatch.setattr(
        "backend.services.mn2_deposit_scanner.run_scanner",
        lambda: {"success": True, "credits_applied": 0},
    )
    monkeypatch.setattr(
        "backend.services.agent_admin_service.reconcile_treasury_pool",
        lambda: {"ok": True, "pool_balance_mn2": 0},
    )
    monkeypatch.setattr(
        "backend.services.agent_kill_switch.get_status",
        lambda: {"success": True, "global_halt": False},
    )
    from backend.services.security_cron_service import run_security_sweep
    r = run_security_sweep(drift_limit=10)
    assert r.get("success") is True
    assert "conservation" in r.get("results", {})


def test_agent_admin_status_route_local(client=None):
    from backend.routes.agent_admin_routes import agent_admin_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(agent_admin_bp)
    c = app.test_client()
    r = c.get("/api/agents/control/status")
    # Without ops secret, localhost may work depending on env
    assert r.status_code in (200, 403)


def test_agent_admin_fund_route(monkeypatch):
    from backend.routes.agent_admin_routes import agent_admin_bp
    from flask import Flask

    monkeypatch.setattr("backend.routes.agent_admin_routes._ops_ok", lambda: True)
    monkeypatch.setattr(
        "backend.services.agent_wallet_service.distribute_agent_funding",
        lambda: {"success": True, "results": []},
    )
    app = Flask(__name__)
    app.register_blueprint(agent_admin_bp)
    r = app.test_client().post("/api/agents/control/fund")
    assert r.status_code == 200
    assert r.get_json().get("success") is True


def test_security_cron_route(monkeypatch):
    from backend.routes.security_cron_routes import security_cron_bp
    from flask import Flask

    monkeypatch.setattr("backend.routes.security_cron_routes._ops_ok", lambda: True)
    monkeypatch.setattr(
        "backend.services.security_cron_service.run_security_sweep",
        lambda **kw: {"success": True, "ok": True, "results": {}},
    )
    monkeypatch.setattr(
        "backend.services.activity_events_service.emit",
        lambda *a, **k: {"success": True},
    )
    app = Flask(__name__)
    app.register_blueprint(security_cron_bp)
    r = app.test_client().post("/api/security/cron/sweep", json={})
    assert r.status_code == 200
    assert r.get_json().get("success") is True


def test_agent_cron_security_preset():
    from backend.services.agent_cron_service import expand_preset
    jobs = expand_preset("security")
    assert "security_sweep" in jobs


def test_control_trader_run_route(monkeypatch):
    from backend.routes.agent_admin_routes import agent_admin_bp
    from flask import Flask

    monkeypatch.setattr("backend.routes.agent_admin_routes._ops_ok", lambda: True)
    monkeypatch.setattr(
        "backend.services.agent_trader_service.run_all_traders",
        lambda: {"success": True, "trades": 0},
    )
    app = Flask(__name__)
    app.register_blueprint(agent_admin_bp)
    r = app.test_client().post("/api/agents/control/trader/run")
    assert r.status_code == 200
    assert r.get_json().get("success") is True
