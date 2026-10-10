"""Unit tests for Facebook casino Messenger webhook bot."""
import hashlib
import hmac

import pytest

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(monkeypatch):
    from flask import Flask
    from backend.routes.facebook_casino_routes import facebook_casino_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(facebook_casino_bp)
    return app


def test_webhook_verify_ok(monkeypatch):
    from backend.services import facebook_casino_bot_service as svc

    svc.reload_config()
    monkeypatch.setenv("FACEBOOK_VERIFY_TOKEN", "test-verify-token")
    assert svc.verify_webhook("subscribe", "test-verify-token", "challenge123") == "challenge123"
    assert svc.verify_webhook("subscribe", "wrong", "challenge123") is None


def test_signature_verify(monkeypatch):
    from backend.services import facebook_casino_bot_service as svc

    monkeypatch.setenv("FACEBOOK_APP_SECRET", "secret123")
    body = b'{"object":"page"}'
    sig = "sha256=" + hmac.new(b"secret123", body, hashlib.sha256).hexdigest()
    ok, err = svc.verify_signature(body, sig)
    assert ok is True
    assert err is None
    bad, err2 = svc.verify_signature(body, "sha256=deadbeef")
    assert bad is False
    assert err2 == "invalid_signature"


def test_build_reply_commands():
    from backend.services.facebook_casino_bot_service import build_reply

    assert "casino" in build_reply("casino").lower()
    assert "shop" in build_reply("shop").lower()
    faq = build_reply("faq deposit")
    assert "Profile" in faq or "deposit" in faq.lower()


def test_handle_webhook_skips_echo(monkeypatch):
    from backend.services import facebook_casino_bot_service as svc

    monkeypatch.setenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
    payload = {
        "object": "page",
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "user1"},
                        "message": {"text": "help", "is_echo": True},
                    }
                ]
            }
        ],
    }
    out = svc.handle_webhook_payload(payload)
    assert out["success"] is True
    assert out["handled"] == 0


def test_webhook_routes_verify(monkeypatch):
    monkeypatch.setenv("FACEBOOK_VERIFY_TOKEN", "route-token")
    app = _app(monkeypatch)
    with app.test_client() as client:
        r = client.get(
            "/api/facebook/casino/webhook",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "route-token",
                "hub.challenge": "abc",
            },
        )
    assert r.status_code == 200
    assert r.get_data(as_text=True) == "abc"


def test_status_route(monkeypatch):
    app = _app(monkeypatch)
    with app.test_client() as client:
        r = client.get("/api/facebook/casino/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert "/api/facebook/casino/webhook" in data["webhook_url"]
