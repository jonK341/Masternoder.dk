"""P0: /api/health/system and /api/health/database respond quickly with HTTP 200."""
from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _health_app():
    from flask import Flask
    from src.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


def test_system_health_returns_200_even_when_mn2_degraded(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.health_check",
        lambda timeout_sec=None: {
            "status": "unreachable",
            "block_height": None,
            "latency_ms": 1.0,
            "error": "stub",
            "credentials": {"user_set": False, "password_set": False},
        },
    )
    app = _health_app()
    with app.test_client() as client:
        r = client.get("/api/health/system")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("overall") in ("healthy", "degraded")
    assert "components" in data
    assert data["components"]["mn2_rpc"]["status"] == "unreachable"


def test_database_health_returns_200_when_db_connected():
    app = _health_app()
    with app.test_client() as client:
        r = client.get("/api/health/database")
    if r.status_code == 503:
        pytest.skip("DB not configured in this test environment")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data["database"]["connected"] is True
    assert "missing_required_tables" in data["database"]
