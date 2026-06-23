"""Owner cockpit route tests."""
from flask import Flask


def _app():
    from backend.routes.owner_panel_routes import owner_panel_bp

    app = Flask(__name__)
    app.secret_key = "test-owner-cockpit"
    app.register_blueprint(owner_panel_bp)
    return app


def test_owner_page_serves_html():
    client = _app().test_client()
    r = client.get("/owner/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Owner Cockpit" in html
    assert "Agent Controllers" in html
    assert "Crypto Controllers" in html
    assert "Model Controllers" in html
    assert "User Controllers" in html
    assert "Tools Controllers" in html


def test_owner_tools_requires_auth(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    client = _app().test_client()
    r = client.get("/owner/api/tools", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403


def test_owner_tools_catalog(monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["owner_ops_authenticated"] = True
    r = client.get("/owner/api/tools", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    snap = data.get("tools") or {}
    tools = snap.get("tools") or []
    assert len(tools) >= 10
    ids = {t["id"] for t in tools}
    assert "debugger" in ids
    assert "register_intelligence" in ids
    assert all("status" in t and "category" in t for t in tools)


def test_owner_tools_audit_tail(monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["owner_ops_authenticated"] = True
    r = client.get("/owner/api/tools/run/audit_tail?limit=5", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("action") == "audit_tail"
    assert isinstance(data.get("rows"), list)


def test_owner_api_requires_auth(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    client = _app().test_client()
    r = client.get("/owner/api/health", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert r.status_code == 403


def test_owner_session_auth_flow(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    monkeypatch.setattr(
        "backend.routes.owner_panel_routes._health_snapshot",
        lambda: {"ts": "2026-01-01T00:00:00Z", "app": {"status": "healthy"}},
    )
    monkeypatch.setattr("backend.routes.owner_panel_routes._recent_audit", lambda limit=8: [])
    client = _app().test_client()

    assert client.get("/owner/api/session").get_json()["authenticated"] is False

    bad = client.post("/owner/api/auth", json={"secret": "wrong"})
    assert bad.status_code == 403

    ok = client.post("/owner/api/auth", json={"secret": "sekrit"})
    assert ok.status_code == 200
    assert client.get("/owner/api/session").get_json()["authenticated"] is True

    health = client.get("/owner/api/health")
    assert health.status_code == 200
    data = health.get_json()
    assert data.get("success") is True
    assert "health" in data


def test_owner_agents_halt_resume(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    state = {"global_halt": False}

    def fake_set_switch(**kwargs):
        if kwargs.get("global_halt") is not None:
            state["global_halt"] = bool(kwargs["global_halt"])
        return {"success": True, "global_halt": state["global_halt"]}

    monkeypatch.setattr("backend.services.agent_kill_switch.set_switch", fake_set_switch)

    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["owner_ops_authenticated"] = True

    halt = client.post("/owner/api/agents/halt", json={"reason": "test"})
    assert halt.status_code == 200
    assert halt.get_json()["kill_switch"]["global_halt"] is True

    resume = client.post("/owner/api/agents/resume")
    assert resume.status_code == 200
    assert resume.get_json()["kill_switch"]["global_halt"] is False


def test_owner_ai_snapshot_localhost(monkeypatch):
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    monkeypatch.setattr(
        "backend.routes.owner_panel_routes._ai_snapshot",
        lambda: {"providers": [], "summary": {"total": 0, "configured": 0, "available": 0}},
    )
    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["owner_ops_authenticated"] = True
    r = client.get("/owner/api/ai", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert "providers" in data.get("ai", {})


def test_owner_crypto_models_users_snapshots(monkeypatch):
    monkeypatch.setenv("ADMIN_OPS_SECRET", "sekrit")
    import backend.routes.owner_panel_routes as opr

    monkeypatch.setattr(opr, "_crypto_snapshot", lambda: {"conservation": {"verdict": "green"}})
    monkeypatch.setattr(opr, "_models_snapshot", lambda: {"summary": {"llm_available": 1}})
    monkeypatch.setattr(opr, "_users_snapshot", lambda: {"customer_aggregator": {"total": 0}})

    client = _app().test_client()
    with client.session_transaction() as sess:
        sess["owner_ops_authenticated"] = True

    for path, key in (
        ("/owner/api/crypto", "crypto"),
        ("/owner/api/models", "models"),
        ("/owner/api/users", "users"),
    ):
        r = client.get(path)
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert key in data

    monkeypatch.setattr(
        "backend.services.mn2_conservation_gate.conservation_gate",
        lambda: {"verdict": "green", "ok": True},
    )
    recheck = client.post("/owner/api/crypto/conservation/recheck")
    assert recheck.status_code == 200
    assert "conservation" in recheck.get_json()

    assert client.post("/owner/api/crypto/treasury/scan", json={}).status_code == 400
    assert client.post(
        "/owner/api/models/providers/reset", json={"provider": "openai"}
    ).status_code == 400
