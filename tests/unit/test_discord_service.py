"""Discord service tests."""
import pytest


def test_post_message_no_webhook(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services.discord_service import post_message

    r = post_message("ops", {"title": "Test", "description": "Hello"}, message_id="test-msg-1")
    assert r.get("success") is True


def test_webhook_for_channel_prefers_per_channel(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/default/secret")
    monkeypatch.setenv("DISCORD_CHANNEL_ID_MARKET", "https://discord.com/api/webhooks/market/secret")
    from backend.services.discord_service import _webhook_for_channel

    url, key = _webhook_for_channel("market")
    assert key == "DISCORD_CHANNEL_ID_MARKET"
    assert url.endswith("/market/secret")


def test_post_message_rejects_numeric_channel_id(monkeypatch, tmp_path):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("DISCORD_CHANNEL_ID_MARKET", "1781797440123456789")
    from backend.services import discord_service as ds

    monkeypatch.setattr(ds, "_OUTBOX", str(tmp_path / "outbox.jsonl"))
    r = ds.post_message("market", {"title": "Test"}, message_id="bad-market-webhook")
    assert r.get("success") is False
    assert "numeric channel ID" in (r.get("error") or "")


def test_post_message_idempotent(monkeypatch, tmp_path):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services import discord_service as ds

    monkeypatch.setattr(ds, "_OUTBOX", str(tmp_path / "outbox.jsonl"))
    r1 = ds.post_message("ops", {"title": "A"}, message_id="dup-1")
    r2 = ds.post_message("ops", {"title": "A"}, message_id="dup-1")
    assert r1.get("success") is True
    assert r2.get("duplicate") is True
