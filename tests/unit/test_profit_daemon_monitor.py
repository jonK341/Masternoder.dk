"""Profit daemon monitor API."""
from __future__ import annotations


def test_profit_daemon_status_route():
    from backend.routes.profit_daemon_routes import profit_daemon_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(profit_daemon_bp)
    client = app.test_client()
    rv = client.get("/api/profit-daemon/status")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("success") is True
    assert "loops" in data


def test_monitor_status_structure():
    from backend.services.profit_daemon_monitor_service import monitor_status
    st = monitor_status()
    assert st.get("success") is True
    assert isinstance(st.get("loops"), list)
    assert isinstance(st.get("stats"), list)
    assert st.get("stat_count", 0) >= 31
    assert "blockers" in st
    assert "profit_readiness_pct" in st
