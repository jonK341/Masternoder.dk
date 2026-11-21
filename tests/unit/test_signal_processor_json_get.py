"""GET /api requests with Content-Type: application/json must not 400.

Profile wallet fetchJson always set Content-Type even on GET. The signal
processor middleware treated is_json as requiring a parseable body and raised
Werkzeug BadRequest before the route ran.
"""
from flask import Flask, jsonify

from backend.middleware.json_error_handler import register_json_error_handlers
from backend.middleware.signal_processor_middleware import register_signal_processor_middleware


def _app(monkeypatch):
    monkeypatch.setenv("DISABLE_PATH_CORRECTION", "1")
    app = Flask(__name__)
    register_json_error_handlers(app)
    register_signal_processor_middleware(app)

    @app.get("/api/mn2/balance")
    def balance():
        return jsonify({"success": True, "mn2_balance": 0}), 200

    return app


def test_api_get_with_json_content_type_does_not_400(monkeypatch):
    client = _app(monkeypatch).test_client()
    response = client.get(
        "/api/mn2/balance?user_id=user_profile_wallet",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.get_json().get("success") is True


def test_api_get_without_content_type_still_ok(monkeypatch):
    client = _app(monkeypatch).test_client()
    response = client.get("/api/mn2/balance?user_id=user_profile_wallet")
    assert response.status_code == 200
