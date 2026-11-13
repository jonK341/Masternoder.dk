"""Explicit ?user_id= must win on prefer_query read paths."""


def test_prefer_query_beats_session(monkeypatch):
    from flask import Flask, session
    from backend.services import account_resolution_service as ars

    app = Flask(__name__)
    app.secret_key = "test"

    with app.test_request_context("/api/mn2/transactions?user_id=user_query_explicit"):
        session["user_id"] = "user_session_other"
        assert ars.resolve_user_id(from_query=True, prefer_query=True) == "user_query_explicit"
        assert ars.resolve_user_id(from_query=True, prefer_query=False) == "user_session_other"
