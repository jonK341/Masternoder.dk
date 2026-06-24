"""MN2 Discord channel config + CLI hooks."""
import json
import os

import pytest


@pytest.fixture
def mn2_config_path(tmp_path, monkeypatch):
    path = tmp_path / "discord_mn2_channel.json"
    monkeypatch.setattr(
        "backend.services.discord_mn2_channel_service._CONFIG_PATH",
        str(path),
    )
    monkeypatch.setattr("backend.services.discord_mn2_channel_service._CACHE", {})
    return path


def test_get_config_defaults(mn2_config_path):
    from backend.services.discord_mn2_channel_service import get_config, reload_config

    reload_config()
    cfg = get_config()
    assert cfg["enabled"] is True
    assert cfg["enabled_streams"]["market"] is True
    assert cfg["enabled_streams"]["social"] is False


def test_set_channel_and_topic(mn2_config_path):
    from backend.services.discord_mn2_channel_service import get_config, set_channel_id, set_topic

    set_channel_id("123456789012345678")
    set_topic("MN2 test topic")
    cfg = get_config()
    assert cfg["channel_id"] == "123456789012345678"
    assert cfg["topic"] == "MN2 test topic"


def test_set_stream_toggle(mn2_config_path):
    from backend.services.discord_mn2_channel_service import set_stream, stream_enabled

    set_stream("social", True)
    assert stream_enabled("social") is True
    set_stream("social", False)
    assert stream_enabled("social") is False


def test_should_mirror_channel(mn2_config_path):
    from backend.services.discord_mn2_channel_service import set_stream, should_mirror_channel

    assert should_mirror_channel("market") is True
    set_stream("market", False)
    assert should_mirror_channel("market") is False
    assert should_mirror_channel("unknown") is False


def test_resolve_webhook_prefers_config(mn2_config_path, monkeypatch):
    monkeypatch.delenv("DISCORD_CHANNEL_ID_MN2", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services.discord_mn2_channel_service import reload_config, resolve_webhook, set_webhook_url

    set_webhook_url("https://discord.com/api/webhooks/mn2/secret")
    reload_config()
    assert resolve_webhook().endswith("/secret")


def test_mirror_post_skips_disabled(mn2_config_path, monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services.discord_mn2_channel_service import mirror_post, set_stream

    set_stream("casino", False)
    assert mirror_post("casino", {"embeds": [{"title": "Win"}]}) is None


def test_build_info_embed(mn2_config_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_services_hub.get_services_catalog",
        lambda use_cache=True: {
            "summary": {"overall": "healthy", "healthy": 3, "total": 3},
            "services": [{"name": "Staking", "status": "active"}],
        },
    )
    from backend.services.discord_mn2_channel_service import build_info_embed

    payload = build_info_embed()
    assert payload["embeds"][0]["title"]
    assert "Staking" in payload["embeds"][0]["description"]


def test_test_post_no_webhook(mn2_config_path, monkeypatch, tmp_path):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.setattr("backend.services.discord_service._OUTBOX", str(tmp_path / "outbox.jsonl"))
    from backend.services.discord_mn2_channel_service import test_post

    r = test_post()
    assert r.get("webhook_configured") is False


def test_slash_mn2_reply(mn2_config_path, monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_services_hub.get_services_catalog",
        lambda use_cache=True: {"summary": {"overall": "healthy", "healthy": 2, "total": 2}, "services": []},
    )
    from backend.services.discord_mn2_channel_service import format_slash_mn2_reply

    text = format_slash_mn2_reply()
    assert "MN2 Hub" in text
    assert "HOSTMN5" in text


def test_discord_service_mn2_webhook(mn2_config_path, monkeypatch):
    monkeypatch.delenv("DISCORD_CHANNEL_ID_MN2", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services.discord_mn2_channel_service import set_webhook_url
    from backend.services.discord_service import _webhook_for_channel

    set_webhook_url("https://discord.com/api/webhooks/mn2/from-json")
    url, key = _webhook_for_channel("mn2")
    assert key == "discord_mn2_channel.json"
    assert "from-json" in url


def test_run_mn2_channel_digest(monkeypatch, mn2_config_path, tmp_path):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.setattr("backend.services.discord_service._OUTBOX", str(tmp_path / "outbox.jsonl"))
    monkeypatch.setattr(
        "backend.services.mn2_services_hub.get_services_catalog",
        lambda use_cache=True: {"summary": {"overall": "healthy", "healthy": 1, "total": 1}, "services": []},
    )
    from backend.services.discord_m8_streams import run_mn2_channel_digest

    r = run_mn2_channel_digest(force=True)
    assert r.get("success") is True
