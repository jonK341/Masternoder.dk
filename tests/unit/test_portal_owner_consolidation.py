"""Portal → Owner Cockpit consolidation route tests."""
from flask import Flask


def _pages_app():
    from backend.routes.all_page_routes import all_page_bp

    app = Flask(__name__)
    app.secret_key = "test-portal-consolidation"
    app.register_blueprint(all_page_bp)
    return app


def test_debugger_redirects_to_owner_when_unauthenticated(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    client = _pages_app().test_client()
    r = client.get("/debugger/", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 302
    assert r.location.endswith("/owner#tools-debugger")


def test_debugger_serves_when_ops_session(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    client = _pages_app().test_client()
    with client.session_transaction() as sess:
        sess["owner_ops_authenticated"] = True
    r = client.get("/debugger/", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 200
    assert r.headers.get("X-Owner-Gated") == "1"


def test_master_control_redirects_to_owner(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    client = _pages_app().test_client()
    r = client.get("/dashboard/master_control/", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 302
    assert "tools-master" in r.location


def test_agents_control_redirects_to_owner_agents_anchor(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    client = _pages_app().test_client()
    r = client.get("/dashboard/agents_control/", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 302
    assert r.location.endswith("/owner#agents")


def test_api_monitor_html_redirects_to_owner(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    from backend.routes.api_monitor_routes import api_monitor_bp

    app = Flask(__name__)
    app.secret_key = "test-api-monitor"
    app.register_blueprint(api_monitor_bp)
    client = app.test_client()
    r = client.get("/api/", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 302
    assert "tools-api" in r.location


def test_point_control_board_api_requires_ops(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    from backend.routes.point_control_board_routes import point_control_board_bp

    app = Flask(__name__)
    app.secret_key = "test-pcb"
    app.register_blueprint(point_control_board_bp)
    client = app.test_client()
    r = client.get("/api/control-board/status", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403
