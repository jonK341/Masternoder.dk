"""Fleet stream live chat API."""
import pytest


@pytest.fixture
def monitor_client(ctl_env, monkeypatch):
    from flask import Flask
    from backend.routes import crypto_exchange_routes as routes

    app = Flask(__name__)
    app.register_blueprint(routes.crypto_exchange_bp)
    return app.test_client()


@pytest.fixture
def ctl_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import trading_bots_control_service as ctl

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(ctl, "_CONTROL_PATH", str(data / "trading_bots_control.json"))
    return {"ex": ex, "arb": arb, "ctl": ctl}


@pytest.fixture
def chat_env(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs" / "fleet_stream_chat"
    log_dir.mkdir(parents=True)
    monkeypatch.setenv("FLEET_PROGRESS_MONITOR_PUBLIC", "1")
    monkeypatch.setattr(
        "backend.services.fleet_stream_chat_service._MSG_DIR",
        str(log_dir),
    )
    monkeypatch.setattr(
        "backend.services.fleet_stream_chat_service._MSG_FILE",
        str(log_dir / "messages.jsonl"),
    )
    monkeypatch.setattr(
        "backend.services.fleet_stream_chat_service._CLAIMS_FILE",
        str(log_dir / "claims.json"),
    )
    monkeypatch.setattr(
        "backend.services.fleet_stream_chat_service._DAILY_FILE",
        str(log_dir / "daily.json"),
    )
    return log_dir


def test_post_and_list_chat(chat_env):
    from backend.services.fleet_stream_chat_service import list_messages, post_message

    r = post_message(channel="live", text="Hello fleet", handle="Tester", guest_id="g_test")
    assert r["success"] is True
    msgs = list_messages(channel="live")
    assert len(msgs) >= 1
    assert msgs[-1]["text"] == "Hello fleet"


def test_bootstrap_has_rewards(chat_env):
    from backend.services.fleet_stream_chat_service import bootstrap

    b = bootstrap()
    assert b["success"] is True
    assert b["rewards"]["event_count"] >= 10
    assert b["youtube"]["video_id"] == "MBjG7hq_YZA"
    assert "embed=" in b["youtube"]["embed_url"] or "/embed/" in b["youtube"]["embed_url"]
    assert "mute=1" in b["youtube"]["embed_url"]
    assert b["youtube"]["watch_url"]


def test_youtube_embed_builder():
    from backend.services.fleet_stream_chat_service import (
        build_youtube_embed_url,
        sanitize_youtube_video_id,
    )

    assert sanitize_youtube_video_id("MBjG7hq_YZA") == "MBjG7hq_YZA"
    assert sanitize_youtube_video_id("bad id!") == ""
    url = build_youtube_embed_url(
        "MBjG7hq_YZA",
        {"embed": {"autoplay": True, "mute": True, "modest_branding": True, "rel": False}},
    )
    assert "MBjG7hq_YZA" in url
    assert "autoplay=1" in url
    assert "modestbranding=1" in url


def test_chat_routes(monitor_client, chat_env, monkeypatch):
    monkeypatch.setattr(
        "backend.services.exchange_fleet_progress_monitor_service.monitor_public_enabled",
        lambda: True,
    )

    def _uid():
        return "default_user"

    monkeypatch.setattr(
        "backend.routes.crypto_exchange_routes._fleet_chat_uid",
        _uid,
    )
    r = monitor_client.get("/api/exchange/fleet-stream/chat/bootstrap")
    assert r.status_code == 200
    assert r.get_json().get("success") is True
    r2 = monitor_client.post(
        "/api/exchange/fleet-stream/chat/messages",
        json={"text": "hi", "handle": "Web", "guest_id": "g1"},
    )
    assert r2.status_code == 200
