"""
Unit tests for the Lab V2.0 first-slice status contract.
Run: pytest tests/unit/test_lab_v2_status.py -v
"""
from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _get_app(monkeypatch):
    from flask import Flask
    from backend.routes import lab_routes

    monkeypatch.setattr(lab_routes, "db", None)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(lab_routes.lab_bp)
    return app


def test_lab_v2_status_default_user_is_read_only_and_successful(monkeypatch):
    app = _get_app(monkeypatch)
    with app.test_client() as c:
        r = c.get("/api/lab/v2/status?user_id=test_user")

    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("version") == "2.0-first-slice"
    assert data.get("rulebook", {}).get("id") == "lab_v2"
    assert data.get("tech", {}).get("read_only_first_slice") is True
    assert data.get("progression", {}).get("tier") == "Novice"
    assert isinstance(data.get("milestones"), list)
    assert data.get("progression", {}).get("next_milestone", {}).get("id") == "first_research"


def test_lab_v2_rulebook_data_has_agent_knowledge_topics(monkeypatch):
    app = _get_app(monkeypatch)
    with app.test_client() as c:
        r = c.get("/api/lab/v2/status?user_id=test_user")

    data = r.get_json()
    rulebook = data.get("rulebook") or {}
    agent_knowledge = data.get("agent_knowledge") or {}
    assert rulebook.get("available") is True
    assert rulebook.get("rule_count", 0) >= 5
    assert agent_knowledge.get("embedded_count", 0) >= 4
    assert agent_knowledge.get("total_count", 0) >= agent_knowledge.get("embedded_count", 0)
