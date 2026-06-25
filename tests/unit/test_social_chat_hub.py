"""Unified social chat hub — config, feed merge, cross-send."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


@pytest.fixture
def hub_env(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = os.path.join(tmp, "social_chat_hub_config.json")
        msg_path = os.path.join(tmp, "messages.json")
        os.makedirs(os.path.dirname(msg_path), exist_ok=True)
        cfg = {
            "room_id": "test_room",
            "max_messages": 100,
            "default_cross_networks": ["site", "casino"],
            "networks": [
                {"id": "site", "label": "Site", "icon": "🌐"},
                {"id": "casino", "label": "Casino", "icon": "🎰"},
                {"id": "discord", "label": "Discord", "icon": "💬"},
            ],
            "fx_effects": [
                {"id": "none", "label": "Plain", "class": ""},
                {"id": "glow", "label": "Glow", "class": "scp-fx-glow"},
            ],
        }
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        import backend.services.social_chat_hub_service as hub

        monkeypatch.setattr(hub, "_CONFIG_PATH", cfg_path)
        monkeypatch.setattr(hub, "_MSG_PATH", msg_path)
        monkeypatch.setattr(hub, "_CROSS_LOG", os.path.join(tmp, "cross_posts.jsonl"))
        monkeypatch.setattr(
            hub,
            "_profile_identity",
            lambda uid: {"display_name": uid or "Player", "avatar": None},
        )
        monkeypatch.setattr(hub, "_legacy_social_messages", lambda limit: [])
        yield hub


def test_get_hub_config(hub_env):
    out = hub_env.get_hub_config()
    assert out["success"] is True
    assert out["room_id"] == "test_room"
    assert len(out["networks"]) >= 2
    assert any(fx["id"] == "glow" for fx in out["fx_effects"])


def test_cross_send_and_unified_feed(hub_env):
    sent = hub_env.cross_send("alice", "Hello casino crew", source_site="casino", fx="glow")
    assert sent["success"] is True
    assert sent["message"]["message"] == "Hello casino crew"
    assert "site" in sent["networks"]
    feed = hub_env.get_unified_feed(limit=10)
    assert feed["success"] is True
    assert len(feed["messages"]) == 1
    assert feed["messages"][0]["fx"] == "glow"


def test_get_monitor_totals(hub_env):
    hub_env.cross_send("bob", "Monitor test", networks=["discord"])
    mon = hub_env.get_monitor()
    assert mon["success"] is True
    assert mon["totals"]["hub_stored"] >= 1
    assert mon["totals"]["by_network"].get("discord", 0) >= 1
