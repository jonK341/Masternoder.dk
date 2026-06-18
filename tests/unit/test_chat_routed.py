"""Main chat route uses routed_chat with LLM fallback."""
import tempfile
from pathlib import Path

import pytest
from flask import Flask


@pytest.fixture
def chat_app(monkeypatch):
    import backend.routes.chat_routes as chat_routes

    with tempfile.TemporaryDirectory(prefix="chat_routed_") as temp_dir:
        monkeypatch.setattr(chat_routes, "CHAT_DATA_DIR", temp_dir)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(chat_routes.chat_bp)
        yield app


def test_chat_send_uses_routed_chat(chat_app, monkeypatch):
    client = chat_app.test_client()

    class _MockResp:
        success = True
        content = "Hello from routed chat!"

    import backend.services.agent_ai_router as router_mod

    monkeypatch.setattr(
        router_mod,
        "routed_chat",
        lambda messages, task_kind, user_id, **kwargs: (
            _MockResp(),
            {"trace_id": "main1", "crypto_reward": {"mn2_awarded": 0.002, "coins_awarded": 5}},
        ),
    )

    res = client.post(
        "/api/chat/send",
        json={"user_id": "chatter", "message": "Hi there", "username": "chatter"},
    )
    body = res.get_json()
    assert res.status_code == 200
    assert body["success"] is True
    assert body["ai_response"] == "Hello from routed chat!"
    assert body.get("reward", {}).get("mn2_awarded") == 0.002


def test_chat_stream_awards_reward_on_done(chat_app, monkeypatch):
    client = chat_app.test_client()

    def _fake_stream(messages, **kwargs):
        yield "Hello "
        yield "stream"

    import backend.services.llm_service as llm_mod

    monkeypatch.setattr(llm_mod, "stream_chat", lambda messages, **kwargs: _fake_stream(messages, **kwargs))
    monkeypatch.setattr(
        "backend.services.agent_crypto_rewards_service.award_agent_action",
        lambda user_id, action, **kwargs: {
            "success": True,
            "mn2_awarded": 0.002,
            "coins_awarded": 5,
            "action": action,
        },
    )

    res = client.post(
        "/api/chat/stream",
        json={"user_id": "streamer", "message": "Hi stream"},
    )
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert '"type": "done"' in body or '"type":"done"' in body
    assert "Hello stream" in body
    assert "reward" in body
