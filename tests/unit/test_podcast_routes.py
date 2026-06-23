"""Podcast HTTP route integration tests."""
from __future__ import annotations

import os
import tempfile

import pytest
from tests.unit.test_utils import ensure_project_root

ensure_project_root()


@pytest.fixture
def podcast_client():
    from flask import Flask
    from backend.routes.podcast_routes import podcast_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(podcast_bp)
    with app.test_client() as client:
        yield client


def test_route_episode_detail_and_play(podcast_client):
    from backend.services.podcast_service import get_episodes

    eps = [e for e in get_episodes() if not e.get("premium")]
    if not eps:
        pytest.skip("no free episodes")
    eid = eps[0]["id"]

    detail = podcast_client.get(f"/api/podcast/episodes/{eid}?user_id=route_play_user")
    assert detail.status_code == 200
    ep = detail.get_json().get("episode") or {}
    assert ep.get("audio_play_url")
    assert ep.get("audio_check", {}).get("play_url")

    play = podcast_client.post(
        f"/api/podcast/episodes/{eid}/play",
        json={"user_id": "route_play_user"},
    )
    assert play.status_code == 200
    assert play.get_json().get("success") is True


def test_route_sound_check_repair_post(podcast_client):
    res = podcast_client.post("/api/podcast/sound-check?repair=1")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["missing"] == 0


def test_route_channels(podcast_client):
    res = podcast_client.get("/api/podcast/channels")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["channels"]) >= 1


def test_route_episodes(podcast_client):
    res = podcast_client.get("/api/podcast/episodes?user_id=route_test_user")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["count"] >= 1
    ep = data["episodes"][0]
    assert ep.get("audio_play_url", "").startswith("/api/podcast/episodes/")


def test_route_sound_check(podcast_client):
    res = podcast_client.get("/api/podcast/sound-check")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["total"] >= 1
    assert "episodes" in data


def test_route_sound_lab(podcast_client):
    res = podcast_client.get("/api/podcast/sound-lab")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["flavor"] == "blue_bubble_cheese_gum"
    assert len(data.get("episodes") or []) >= 1


def test_route_rss_xml(podcast_client):
    res = podcast_client.get("/api/podcast/rss.xml")
    assert res.status_code == 200
    assert res.content_type.startswith("application/rss+xml")
    body = res.get_data(as_text=True)
    assert "MasterNoder Podcast" in body
    assert "<item>" in body


def test_route_transcript_and_chapters(podcast_client):
    from backend.services.podcast_service import get_episodes

    eps = get_episodes()
    if not eps:
        pytest.skip("no episodes")
    eid = eps[0]["id"]

    tr = podcast_client.get(f"/api/podcast/episodes/{eid}/transcript")
    assert tr.status_code == 200
    assert tr.get_json().get("transcript")

    ch = podcast_client.get(f"/api/podcast/episodes/{eid}/chapters")
    assert ch.status_code == 200
    assert len(ch.get_json().get("chapters") or []) >= 1


def test_route_stream_audio(podcast_client):
    from backend.services.podcast_service import get_episodes

    eps = get_episodes()
    if not eps:
        pytest.skip("no episodes")
    eid = eps[0]["id"]

    res = podcast_client.get(f"/api/podcast/episodes/{eid}/audio")
    assert res.status_code == 200
    assert res.content_type.startswith("audio/")
    assert len(res.data) > 500


def test_route_leaderboard(podcast_client):
    res = podcast_client.get("/api/podcast/leaderboard?limit=10")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "leaderboard" in data


def test_route_news_and_comment(podcast_client):
    news = podcast_client.get("/api/podcast/news?limit=3")
    assert news.status_code == 200
    items = news.get_json().get("news") or []
    if not items:
        pytest.skip("no platform news")
    nid = items[0]["id"]

    post = podcast_client.post(
        f"/api/podcast/news/{nid}/comments",
        json={"user_id": "route_news_user", "content": "Route test komment on news"},
    )
    assert post.status_code == 200
    assert post.get_json().get("success") is True

    comments = podcast_client.get(f"/api/podcast/news/{nid}/comments")
    assert comments.status_code == 200
    assert len(comments.get_json().get("comments") or []) >= 1


def test_route_portal_lines(podcast_client):
    res = podcast_client.get("/api/podcast/portal-lines?site=generator")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data.get("line")
    assert data.get("flavor") == "blue_bubble_cheese_gum"


def test_bbcg_flavor_tone_writes_wav():
    from backend.services.podcast_audio_service import _write_bbcg_flavor_tone, probe_audio_file

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        ok = _write_bbcg_flavor_tone(path, duration_sec=0.5, primary_freq=220.0)
        assert ok is True
        meta = probe_audio_file(path)
        assert meta.get("ok") is True
        assert meta.get("format") == "wav"
        assert meta.get("bytes", 0) > 100
        assert meta.get("duration_sec") is not None
    finally:
        if os.path.isfile(path):
            os.remove(path)


def test_probe_audio_on_episode_mp3():
    from backend.services.podcast_audio_service import probe_audio_file, check_episode_audio
    from backend.services.podcast_service import get_episodes

    eps = get_episodes()
    if not eps:
        pytest.skip("no episodes")
    chk = check_episode_audio(eps[0])
    if chk.get("status") != "ok" or not chk.get("path"):
        pytest.skip("no audio on disk")
    meta = probe_audio_file(chk["path"])
    assert meta.get("ok") is True
    assert meta.get("format") == "mp3"
    assert meta.get("bbcg_flavor") is True
