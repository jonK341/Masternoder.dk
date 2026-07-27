"""YouTube stream agent + fleet monitor controls."""
import json
from pathlib import Path

import pytest
from flask import Flask


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def yt_client():
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    app = Flask(__name__)
    app.register_blueprint(crypto_exchange_bp)
    return app.test_client()


def test_youtube_stream_controls_payload(yt_client):
    res = yt_client.get("/api/exchange/youtube-stream/controls")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    mon = data["monitor"]
    assert "mode=stream" in mon["stream_layout"]
    assert mon["obs_browser"].endswith("/streamer/?obs=1")
    assert data["primary_agent"] == "youtube_stream_agent"
    assert len(data.get("skill_set") or []) >= 1


def test_youtube_stream_agent_tools(yt_client):
    res = yt_client.get("/api/exchange/youtube-stream/agent-tools")
    assert res.status_code == 200
    tools = res.get_json().get("tools") or []
    actions = {t["action"] for t in tools}
    assert "monitor_status" in actions
    assert "stream_urls" in actions


def test_youtube_stream_narration_action(yt_client):
    res = yt_client.post(
        "/api/exchange/youtube-stream/agent-action",
        json={"action": "narration_line"},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body.get("line")


def test_youtube_stream_config_file():
    data = json.loads((ROOT / "data/youtube_stream_agent.json").read_text(encoding="utf-8"))
    assert "youtube_stream_agent" in (data.get("agents") or [])
    assert len(data.get("checklist") or []) >= 3


def test_platform_news_youtube_stream_agent_story():
    data = json.loads((ROOT / "data/platform_news.json").read_text(encoding="utf-8"))
    story = next(
        (i for i in (data.get("items") or []) if i.get("id") == "news-youtube-stream-agent-5d-20260726"),
        None,
    )
    assert story is not None
    assert story["href"] == "/streamer/"
