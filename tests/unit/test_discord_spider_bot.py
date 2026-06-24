"""Casino Play App spider bot — Discord + platform_news announce."""
from __future__ import annotations

import pytest


def test_spider_bot_posts_casino_channel(monkeypatch):
    import backend.services.discord_m8_streams as m8

    posted = {}

    def fake_publish(**kw):
        return {"success": True, "item": {"id": kw.get("item_id")}}

    def fake_post(channel, payload, message_id=None):
        posted["channel"] = channel
        posted["message_id"] = message_id
        return {"success": True}

    monkeypatch.setattr("backend.services.platform_news_publish.publish", fake_publish)
    monkeypatch.setattr("backend.services.discord_service.post_message", fake_post)

    out = m8.run_casino_play_app_spider_bot(play_store_url="https://play.example/app")
    assert out["success"] is True
    assert "play.example" in out["play_store_url"]
    assert posted.get("channel") == "casino"
    assert str(posted.get("message_id", "")).startswith("spider-play-app:")
