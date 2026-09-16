"""Unit tests for ledger agent chat threads."""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def agent_env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    threads = data / "ledger_agent_threads.json"
    ledger = data / "discord_fulfillment_ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "ledger_row_id": "discord:chat1",
                        "discord_id": "chat1",
                        "user_id": "u-chat",
                        "display_name": "Chat User",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    import backend.services.ledger_agent_service as las
    import backend.services.discord_fulfillment_ledger_service as dfl

    monkeypatch.setattr(las, "_BASE", str(tmp_path))
    monkeypatch.setattr(las, "_THREADS_FILE", str(threads))
    monkeypatch.setattr(dfl, "_BASE", str(tmp_path))
    monkeypatch.setattr(dfl, "_data_dir", lambda: str(data))
    monkeypatch.setattr(dfl, "_ledger_path", lambda: str(ledger))
    yield threads


def test_post_and_get_thread(agent_env):
    from backend.services.ledger_agent_service import get_thread, post_chat_message

    out = post_chat_message("discord:chat1", "Hello from agent", sender="agent", sender_id="agent-1")
    assert out["success"] is True
    thread = get_thread("discord:chat1")
    assert len(thread.get("messages") or []) == 1
    assert thread["messages"][0]["text"] == "Hello from agent"


def test_auto_greet(agent_env):
    from backend.services.ledger_agent_service import auto_greet, get_thread

    greet = auto_greet("discord:chat1")
    assert greet["success"] is True
    thread = get_thread("discord:chat1")
    assert thread.get("greeted") is True
    assert "MN2 community offer" in (thread.get("messages") or [{}])[0].get("text", "")


def test_auto_greet_skips_duplicate(agent_env):
    from backend.services.ledger_agent_service import auto_greet

    auto_greet("discord:chat1")
    second = auto_greet("discord:chat1")
    assert second.get("skipped") is True
