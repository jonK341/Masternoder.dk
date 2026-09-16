"""
Lab V2.1 hub endpoints — news, systems-check, idea-board.
Run: pytest tests/unit/test_lab_hub_v21.py -v
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


def test_lab_v21_status_version(monkeypatch):
    app = _get_app(monkeypatch)
    with app.test_client() as c:
        r = c.get("/api/lab/v2/status?user_id=test_user")
    data = r.get_json()
    assert r.status_code == 200
    assert data.get("version") == "2.1-hub-upgrade"


def test_lab_news_returns_lab_channel_items(monkeypatch):
    app = _get_app(monkeypatch)
    with app.test_client() as c:
        r = c.get("/api/lab/news?limit=5")
    data = r.get_json()
    assert r.status_code == 200
    assert data.get("success") is True
    assert data.get("channel") == "lab"
    assert isinstance(data.get("news"), list)
    assert len(data.get("news")) >= 1


def test_lab_systems_check_runs_checks(monkeypatch):
    app = _get_app(monkeypatch)
    with app.test_client() as c:
        r = c.get("/api/lab/systems-check?user_id=test_user")
    data = r.get_json()
    assert r.status_code == 200
    assert data.get("success") is True
    assert isinstance(data.get("checks"), list)
    assert data.get("total", 0) >= 3


def test_lab_idea_board_get_empty_without_db(monkeypatch):
    app = _get_app(monkeypatch)
    with app.test_client() as c:
        r = c.get("/api/lab/idea-board?user_id=test_user")
    data = r.get_json()
    assert r.status_code == 200
    assert data.get("success") is True
    assert data.get("ideas") == []


def test_lab_catalog_has_chapter5_upgrades():
    from backend.routes.lab_routes import _load_lab_catalog

    catalog = _load_lab_catalog()
    c5 = [u for u in catalog if str(u.get("id", "")).startswith("c5_")]
    assert len(c5) == 25
