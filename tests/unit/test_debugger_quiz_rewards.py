"""Debugger Q&A MN2 reward tests."""
import pytest


def test_quiz_rejects_anonymous():
    from backend.routes.debugger_quiz_routes import debugger_quiz_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(debugger_quiz_bp)
    c = app.test_client()
    r = c.post("/api/debugger/quiz/submit", json={"user_id": "default_user", "correct": 40, "total": 50})
    assert r.status_code == 403


def test_quiz_awards_mn2(tmp_path, monkeypatch):
    from backend.routes.debugger_quiz_routes import debugger_quiz_bp
    from backend.services import unified_points_database as upd
    from flask import Flask
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)

    app = Flask(__name__)
    app.register_blueprint(debugger_quiz_bp)
    c = app.test_client()
    r = c.post("/api/debugger/quiz/submit", json={"user_id": "quiz_user", "correct": 45, "total": 50, "day": "2026-06-14"})
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert float(data.get("mn2_awarded") or 0) > 0
