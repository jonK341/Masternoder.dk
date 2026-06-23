"""Gate A + orchestrator infrastructure tests."""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _health_app():
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    from backend.routes.health_routes import health_bp
    app.register_blueprint(health_bp)
    return app


def test_api_health():
    app = _health_app()
    with app.test_client() as c:
        r = c.get("/api/health")
        assert r.status_code == 200
        assert r.get_json().get("success") is True


def test_api_mn2_health():
    app = _health_app()
    with app.test_client() as c:
        r = c.get("/api/mn2/health")
        assert r.status_code in (200, 503)
        data = r.get_json()
        assert data.get("success") is True
        assert "components" in data
        assert "mn2_rpc" in data["components"]


def test_themes_user_route():
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    from backend.routes.missing_endpoints_routes import themes_user
    app.add_url_rule("/api/themes/user", "themes_user", themes_user, methods=["GET"])
    with app.test_client() as c:
        r = c.get("/api/themes/user?user_id=default_user")
        assert r.status_code == 200
        assert r.get_json().get("success") is True


def test_unified_points_idempotency(monkeypatch):
    from backend.services import unified_points_database as upd

    uid = "_test_idem_user"
    base = os.path.join(_ROOT, "data", "_test_upd_idem")
    os.makedirs(base, exist_ok=True)
    db = upd.UnifiedPointsDatabase(base_dir=base)
    monkeypatch.setattr(upd, "_IDEMPOTENCY_CACHE", {})
    ref = "test-ref-001"
    meta = {"reference": ref}
    a = db.add_points(uid, "mn2_balance", 1.0, source="test", metadata=meta)
    b = db.add_points(uid, "mn2_balance", 1.0, source="test", metadata=meta)
    assert a.get("success") is True
    assert b.get("duplicate") is True
    try:
        import shutil
        shutil.rmtree(base, ignore_errors=True)
    except Exception:
        pass


def test_discord_service_post_without_webhook():
    from backend.services import discord_service as ds
    result = ds.post_message("ops", {"content": "test"}, message_id="unit-test-msg-1")
    assert result.get("success") is True


def test_game_mn2_rewards_rejects_anon():
    from backend.services.game_mn2_rewards import credit_mn2
    r = credit_mn2("default_user", 0.01, source="battle_win", reference="t1")
    assert r.get("success") is False


def test_agent_wallet_credit():
    from backend.services import agent_wallet_service as aw
    path = os.path.join(_ROOT, "data", "_test_agent_wallets.json")
    old = aw._WALLETS_FILE
    aw._WALLETS_FILE = path
    try:
        if os.path.isfile(path):
            os.remove(path)
        r = aw.credit("trader_agent_1", 100.0, reference="unit-test", source="test")
        assert r.get("success") is True
        assert aw.get_balance("trader_agent_1") == 100.0
    finally:
        aw._WALLETS_FILE = old
        if os.path.isfile(path):
            os.remove(path)


def test_staking_advisor_refresh():
    from backend.services.ai_staking_advisor_service import refresh_advice
    cache_path = os.path.join(_ROOT, "data", "_test_staking_advisor_cache.json")
    old = None
    import backend.services.ai_staking_advisor_service as sa
    old = sa._CACHE
    sa._CACHE = cache_path
    try:
        if os.path.isfile(cache_path):
            os.remove(cache_path)
        r = refresh_advice("advisor_test_user")
        assert r.get("success") is True
        assert "disclaimer" in r
        assert r.get("recommendation") in ("hold", "consider_stake")
    finally:
        sa._CACHE = old
        if os.path.isfile(cache_path):
            os.remove(cache_path)


def test_activity_events_emit():
    from backend.services import activity_events_service as aes
    log = os.path.join(_ROOT, "logs", "_test_activity_events.jsonl")
    old = aes._LOG_PATH
    aes._LOG_PATH = log
    try:
        if os.path.isfile(log):
            os.remove(log)
        aes.emit("unit_test", user_id="u1", text="hello")
        rows = aes.recent(5)
        assert len(rows) == 1
        assert rows[0]["type"] == "unit_test"
    finally:
        aes._LOG_PATH = old
        if os.path.isfile(log):
            os.remove(log)
