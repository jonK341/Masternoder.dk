"""Regression checks for broken routes, HTTP errors, admin gates, and slow-path bounds."""
import time

from flask import Flask, jsonify


def _client_with(*blueprints, secret_key="test"):
    app = Flask(__name__)
    app.secret_key = secret_key
    for bp in blueprints:
        app.register_blueprint(bp)
    return app.test_client()


def test_method_not_allowed_stays_405():
    from backend.middleware.error_logging_middleware import register_error_logging_middleware
    from backend.middleware.json_error_handler import register_json_error_handlers

    app = Flask(__name__)

    @app.route("/api/market/fill", methods=["POST"])
    def fill():
        return jsonify({"success": True})

    register_json_error_handlers(app)
    register_error_logging_middleware(app)
    response = app.test_client().get("/api/market/fill")
    assert response.status_code == 405
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == "Method Not Allowed"


def test_frontend_gap_routes_exist():
    from backend.routes.agent_automation_routes import agent_automation_bp
    from backend.routes.agent_profile_routes import agent_profile_bp
    from backend.routes.all_page_routes import all_page_bp
    from backend.routes.casino_routes import casino_bp
    from backend.routes.debugger_shell_routes import debugger_shell_bp
    from backend.routes.hunters_game import hunters_game_bp
    from backend.routes.lab_routes import lab_bp
    from backend.routes.manager_secretary_routes import manager_secretary_bp
    from backend.routes.missing_endpoints_routes import missing_endpoints_bp
    from backend.routes.mn2_masternode_routes import mn2_masternode_bp
    from backend.routes.mn2_routes import mn2_bp
    from backend.routes.podcast_routes import podcast_bp

    client = _client_with(
        agent_automation_bp,
        agent_profile_bp,
        all_page_bp,
        casino_bp,
        debugger_shell_bp,
        hunters_game_bp,
        lab_bp,
        manager_secretary_bp,
        missing_endpoints_bp,
        mn2_masternode_bp,
        mn2_bp,
        podcast_bp,
    )
    rules = {rule.rule for rule in client.application.url_map.iter_rules()}
    expected = {
        "/api/agents/rewards/info",
        "/api/agents/skillsets/all",
        "/api/agents/manager/status",
        "/api/game/crypto/level-rewards",
        "/api/lab/idea-board",
        "/api/lab/news",
        "/api/lab/systems-check",
        "/api/mn2/masternode/checkout/config",
        "/api/mn2/masternode/checkout/quote",
        "/api/mn2/masternode/checkout/pay-onchain",
        "/api/mn2/masternode/service",
        "/api/mn2/services",
        "/api/mn2/wallet/refresh",
        "/api/exchange/paypal/mn2-packs",
        "/api/casino/rival-board",
        "/api/podcast/portal-lines",
        "/api/ai-agents",
        "/api/debugger/agent",
        "/api/debugger/profile",
        "/api/debugger/tasks",
        "/api/debug",
        "/api/debugging",
        "/api/horoscope",
        "/api/teleport",
        "/api/make/coffee",
        "/staking",
    }
    missing = expected - rules
    assert not missing, missing


def test_staking_page_redirects():
    from backend.routes.all_page_routes import all_page_bp

    client = _client_with(all_page_bp)
    response = client.get("/staking", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["Location"].endswith("/staking-monitor")


def test_lab_news_and_rewards_info():
    from backend.routes.agent_profile_routes import agent_profile_bp
    from backend.routes.lab_routes import lab_bp

    client = _client_with(lab_bp, agent_profile_bp)
    news = client.get("/api/lab/news?limit=2")
    assert news.status_code == 200
    body = news.get_json()
    assert body["channel"] == "lab"
    assert body["news"]
    rewards = client.get("/api/agents/rewards/info")
    assert rewards.status_code == 200
    assert "first_post" in rewards.get_json()["actions_mn2"]


def test_debug_index_requires_admin(monkeypatch):
    from backend.routes.debugger_shell_routes import debugger_shell_bp

    monkeypatch.setenv("DEBUGGER_ADMIN_KEY", "test-admin-key")
    client = _client_with(debugger_shell_bp)
    locked = client.get("/api/debug")
    assert locked.status_code == 401
    opened = client.get("/api/debug", headers={"X-Admin-Key": "test-admin-key"})
    assert opened.status_code == 200
    assert opened.get_json()["success"] is True
    coffee = client.get("/api/make/coffee", headers={"X-Admin-Key": "test-admin-key"})
    assert coffee.status_code == 418


def test_anonymous_reads_are_401():
    from backend.routes.cogs_routes import cogs_bp
    from backend.routes.discord_routes import discord_bp
    from backend.routes.mn2_onramp_routes import mn2_onramp_bp

    client = _client_with(discord_bp, cogs_bp, mn2_onramp_bp)
    assert client.get("/api/discord/link/status").status_code == 401
    assert client.get("/api/monetization/usage-allowance").status_code == 401
    assert client.get("/api/mn2/onramp/quote").status_code == 401
    assert client.get("/api/discord/link/status?user_id=default_user").status_code == 401


def test_error_dict_shortens_ids():
    from src.db.models_error_logging import _short_identifier

    assert _short_identifier(None) is None
    assert _short_identifier("abc") == "****"
    assert _short_identifier("session-secret-value") == "…alue"


def test_remember_bounds_wait_then_serves_cache():
    from backend.services.bounded_cache import clear_cache, remember

    clear_cache()

    def slow():
        time.sleep(0.6)
        return {"success": True, "n": 7}

    started = time.monotonic()
    first = remember("slow-key", 30, slow, timeout=0.15, fallback={"success": False, "error": "timeout"})
    assert time.monotonic() - started < 0.5
    assert first.get("pending") is True
    time.sleep(0.7)
    second = remember("slow-key", 30, slow, timeout=0.15, fallback={"success": False})
    assert second.get("n") == 7
    assert second.get("cached") is True
    clear_cache()


def test_rpcpassword_examples_are_placeholders():
    from pathlib import Path

    conf = Path("config/masternoder2.conf.example").read_text(encoding="utf-8").splitlines()
    assert conf[6] == "rpcpassword=CHANGE_ME_STRONG_PASSWORD"
    docs = Path("docs/MN2_CONFIG_AND_PASSWORD_STEPS.md").read_text(encoding="utf-8").splitlines()
    assert "CHANGE_ME_STRONG_PASSWORD" in docs[37]
    assert "rpcpassword=" in docs[37]


def test_risk_panel_503_when_no_admin_secret(monkeypatch):
    from backend.routes.ai_assist_routes import ai_assist_bp

    monkeypatch.delenv("COGS_ADMIN_REPORT_KEY", raising=False)
    monkeypatch.delenv("EXCHANGE_ADMIN_KEY", raising=False)
    monkeypatch.delenv("DEBUGGER_ADMIN_KEY", raising=False)
    client = _client_with(ai_assist_bp)
    response = client.get("/api/admin/risk/summary")
    assert response.status_code == 503
    assert response.get_json()["error"] == "admin_risk_disabled"
