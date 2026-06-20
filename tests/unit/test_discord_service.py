"""Discord service tests."""
import pytest


def test_post_message_no_webhook(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services.discord_service import post_message

    r = post_message("ops", {"title": "Test", "description": "Hello"}, message_id="test-msg-1")
    assert r.get("success") is True


def test_post_message_idempotent(monkeypatch, tmp_path):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services import discord_service as ds

    monkeypatch.setattr(ds, "_OUTBOX", str(tmp_path / "outbox.jsonl"))
    r1 = ds.post_message("ops", {"title": "A"}, message_id="dup-1")
    r2 = ds.post_message("ops", {"title": "A"}, message_id="dup-1")
    assert r1.get("success") is True
    assert r2.get("duplicate") is True
