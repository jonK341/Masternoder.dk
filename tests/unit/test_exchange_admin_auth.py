"""Shared exchange admin auth — header-only, timing-safe key check."""
from __future__ import annotations

import pytest
from flask import Flask

from backend.services.exchange_admin_auth import admin_authorized


@pytest.fixture()
def app():
    return Flask(__name__)


def test_denied_when_no_key_configured(app, monkeypatch):
    monkeypatch.delenv("EXCHANGE_ADMIN_KEY", raising=False)
    monkeypatch.delenv("COGS_ADMIN_REPORT_KEY", raising=False)
    with app.test_request_context(headers={"X-Exchange-Admin-Key": "anything"}):
        assert admin_authorized() is False


def test_header_accepted(app, monkeypatch):
    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", "sekret")
    with app.test_request_context(headers={"X-Exchange-Admin-Key": "sekret"}):
        assert admin_authorized() is True
    with app.test_request_context(headers={"X-Admin-Key": "sekret"}):
        assert admin_authorized() is True


def test_wrong_key_rejected(app, monkeypatch):
    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", "sekret")
    with app.test_request_context(headers={"X-Exchange-Admin-Key": "nope"}):
        assert admin_authorized() is False


def test_query_string_key_rejected(app, monkeypatch):
    """Query-string keys leak into logs; only headers are accepted."""
    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", "sekret")
    with app.test_request_context("/?admin_key=sekret"):
        assert admin_authorized() is False


def test_cogs_fallback_key(app, monkeypatch):
    monkeypatch.delenv("EXCHANGE_ADMIN_KEY", raising=False)
    monkeypatch.setenv("COGS_ADMIN_REPORT_KEY", "cogs-key")
    with app.test_request_context(headers={"X-Exchange-Admin-Key": "cogs-key"}):
        assert admin_authorized() is True


def test_critical_check_route_requires_admin(monkeypatch):
    """The critical-top25 checklist write must be owner-gated."""
    monkeypatch.setenv("EXCHANGE_ADMIN_KEY", "sekret")
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    app = Flask(__name__)
    app.register_blueprint(crypto_exchange_bp)
    client = app.test_client()

    rv = client.post("/api/exchange/profit-path/critical-top25/check", json={"id": "x"})
    assert rv.status_code == 401
