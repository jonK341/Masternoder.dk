"""Debugger Q&A MN2 reward tests."""
from contextlib import contextmanager

from flask import Flask


def test_quiz_rejects_anonymous():
    from backend.routes.debugger_quiz_routes import debugger_quiz_bp

    app = Flask(__name__)
    app.register_blueprint(debugger_quiz_bp)
    c = app.test_client()
    r = c.post("/api/debugger/quiz/submit", json={"user_id": "default_user", "correct": 40, "total": 50})
    assert r.status_code == 403


def test_quiz_awards_mn2(tmp_path, monkeypatch):
    from backend.routes.debugger_quiz_routes import debugger_quiz_bp
    from backend.services import unified_points_database as upd

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)
    monkeypatch.setattr("backend.services.mn2_ledger.append_entry", lambda *a, **k: {"success": True})
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: {"success": True})

    app = Flask(__name__)
    app.register_blueprint(debugger_quiz_bp)
    c = app.test_client()
    r = c.post(
        "/api/debugger/quiz/submit",
        json={"user_id": "quiz_user", "correct": 45, "total": 50, "day": "2026-06-14"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert float(data.get("mn2_awarded") or 0) > 0

    # Anti-farm: same day duplicate rejected
    r2 = c.post(
        "/api/debugger/quiz/submit",
        json={"user_id": "quiz_user", "correct": 45, "total": 50, "day": "2026-06-14"},
    )
    assert r2.status_code == 429
    assert r2.get_json().get("error") == "already_rewarded_today"


def test_quiz_score_too_low():
    from backend.routes.debugger_quiz_routes import debugger_quiz_bp

    app = Flask(__name__)
    app.register_blueprint(debugger_quiz_bp)
    c = app.test_client()
    r = c.post("/api/debugger/quiz/submit", json={"user_id": "quiz_user", "correct": 10, "total": 50})
    assert r.status_code == 400
    assert r.get_json().get("error") == "score_too_low"
