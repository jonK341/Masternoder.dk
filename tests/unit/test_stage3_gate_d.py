"""Stage 3 Gate D and avatar backfill tests."""
import json

import pytest


def test_customer_avatar_ensure(tmp_path, monkeypatch):
    import backend.services.customer_avatar_service as cas

    out = tmp_path / "customers"
    monkeypatch.setattr(cas, "_CUSTOMERS_DIR", str(out))
    r = cas.ensure_avatar("user_avatar_test")
    assert r.get("success") is True
    assert r.get("created") is True
    assert (out / "user_avatar_test.svg").is_file()

    r2 = cas.ensure_avatar("user_avatar_test")
    assert r2.get("created") is False


def test_customer_avatar_backfill(tmp_path, monkeypatch):
    import backend.services.customer_avatar_service as cas

    points = tmp_path / "points"
    points.mkdir()
    (points / "cust_x.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "customers"
    monkeypatch.setattr(cas, "_POINTS_DIR", str(points))
    monkeypatch.setattr(cas, "_CUSTOMERS_DIR", str(out))

    r = cas.backfill_missing_avatars(limit=5)
    assert r.get("success") is True
    assert r.get("created") == 1


def test_gate_d_status_service():
    from backend.services.gate_d_status_service import check_gate_d

    r = check_gate_d()
    assert r.get("success") is True
    assert r.get("gate") == "D"
    assert isinstance(r.get("checks"), list)
    assert len(r["checks"]) >= 5


def test_gate_d_health_route():
    from backend.routes.health_routes import health_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(health_bp)
    r = app.test_client().get("/api/health/gate-d")
    assert r.status_code in (200, 503)
    data = r.get_json()
    assert data.get("gate") == "D"
    assert "ready_for_stage_4" in data


def test_trader_leveling_helpers():
    from backend.services.agent_trader_service import (
        _max_open_sells_for_level,
        _sell_amount_for_level,
        trader_level_for_agent,
    )

    assert trader_level_for_agent("trader_agent_1") >= 1
    assert _max_open_sells_for_level(1) == 2
    assert _max_open_sells_for_level(5) == 6
    assert _sell_amount_for_level(10, 3) > 10


def test_security_sweep_includes_avatar_backfill(monkeypatch):
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
        lambda: {"success": True},
    )
    monkeypatch.setattr(
        "backend.services.agent_admin_service.reconcile_treasury_pool",
        lambda: {"ok": True},
    )
    monkeypatch.setattr(
        "backend.services.agent_kill_switch.get_status",
        lambda: {"success": True, "global_halt": False},
    )
    monkeypatch.setattr(
        "backend.services.customer_avatar_service.backfill_missing_avatars",
        lambda **kw: {"success": True, "created": 0},
    )
    from backend.services.security_cron_service import run_security_sweep

    r = run_security_sweep()
    assert "customer_avatar_backfill" in r.get("results", {})
