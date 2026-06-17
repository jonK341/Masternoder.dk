"""Camgirls AI agent integration tests."""
from flask import Flask

from backend.routes.camgirls_routes import camgirls_bp
from backend.services.camgirls_agents_service import (
    agent_for_performer,
    execute_agent_action,
    list_agent_models,
    persona_system_prompt,
)


def test_list_agent_models():
    agents = list_agent_models()
    assert len(agents) >= 2
    assert agents[0].get("agent_id")


def test_agent_for_performer():
    m = agent_for_performer("performer_nova")
    assert m is not None
    assert m.get("agent_id") == "camgirl_agent_nova"


def test_persona_system_prompt():
    row = {"id": "performer_nova", "display_name": "Nova Star", "bio": "Test bio"}
    system, task = persona_system_prompt(row)
    assert "Nova Star" in system
    assert task in ("speed", "free", "default")


def test_execute_agent_action_catalog():
    r = execute_agent_action("catalog", "test_user")
    assert r.get("success") is True
    assert "performers" in r


def test_execute_agent_action_mutating_requires_approved():
    r = execute_agent_action("chat", "test_user", performer_id="p1", message="hi")
    assert r.get("error") == "mutating_action_requires_approved_true"


def test_agent_tools_route():
    app = Flask(__name__)
    app.register_blueprint(camgirls_bp)
    client = app.test_client()
    tools = client.get("/api/camgirls/agent-tools")
    assert tools.status_code == 200
    data = tools.get_json()
    assert data.get("success") is True
    assert any(t.get("action") == "chat" for t in data.get("tools") or [])


def test_agents_roster_route():
    app = Flask(__name__)
    app.register_blueprint(camgirls_bp)
    client = app.test_client()
    r = client.get("/api/camgirls/agents")
    assert r.status_code == 200
    assert (r.get_json() or {}).get("count", 0) >= 2
