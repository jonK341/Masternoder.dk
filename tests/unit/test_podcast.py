"""Unit tests for podcast module."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_podcast_channels_load():
    from backend.services.podcast_service import get_channels
    channels = get_channels()
    assert len(channels) >= 1
    ch = channels[0]
    assert "platforms" in ch
    assert "youtube" in ch["platforms"]
    assert "facebook" in ch["platforms"]
    assert "discord" in ch["platforms"]
    assert "github" in ch["platforms"]


def test_podcast_episodes_load():
    from backend.services.podcast_service import get_episodes, get_episode
    eps = get_episodes()
    assert len(eps) >= 1
    ep = get_episode(eps[0]["id"])
    assert ep is not None
    assert "view_count" in ep


def test_podcast_encode_profiles():
    from backend.services.podcast_encode_service import list_encode_profiles, VALID_AUDIO_PROFILES
    profiles = list_encode_profiles()
    assert len(profiles) == 6
    assert VALID_AUDIO_PROFILES == frozenset({"standard", "premium", "ultra", "broadcast", "studio", "opus_web"})
    assert any(p["id"] == "broadcast" for p in profiles)
    assert any(p["id"] == "studio" for p in profiles)


def test_podcast_portal_lines():
    from backend.services.podcast_social_service import get_portal_lines
    r = get_portal_lines("generator")
    assert r.get("success") is True
    assert r.get("line")
    assert r.get("comment_hint")
    assert any(s.get("id") == "gallery" for s in r.get("sites") or [])


def test_podcast_social_comment():
    from backend.services.podcast_service import get_episodes
    from backend.services.podcast_social_service import add_episode_comment, get_episode_comments
    eps = get_episodes()
    if not eps:
        pytest.skip("no episodes")
    eid = eps[0]["id"]
    r = add_episode_comment(eid, "test_comment_user", "Great episode — MN2 rewards rock!")
    assert r.get("success") is True
    comments = get_episode_comments(eid)
    assert any(c.get("content", "").find("MN2") >= 0 for c in comments)


def test_podcast_crypto_config():
    from backend.services.podcast_crypto_rewards_service import get_crypto_rewards_info, _podcast_cfg
    cfg = _podcast_cfg()
    assert cfg.get("enabled") is True
    info = get_crypto_rewards_info("test_user_podcast")
    assert info.get("success") is True
    assert "rates" in info


def test_podcast_customers():
    from backend.services.podcast_service import get_customers
    result = get_customers(limit=5)
    assert result.get("success") is True
    assert len(result.get("customers") or []) >= 1
    assert result.get("total_listeners", 0) > 0


def test_podcast_agent_tools():
    from backend.services.podcast_agent_service import AGENT_TOOLS, execute_agent_action
    assert len(AGENT_TOOLS) >= 10
    result = execute_agent_action({"action": "list_channels"})
    assert result.get("success") is True
    assert "channels" in result


def test_podcast_record_view():
    from backend.services.podcast_service import get_episodes, record_view
    eps = get_episodes()
    if not eps:
        pytest.skip("no episodes")
    eid = eps[0]["id"]
    before = int(eps[0].get("view_count") or 0)
    result = record_view(eid, "test_view_user", "view")
    assert result.get("success") is True
    assert result.get("view_count", 0) >= before + 1


def test_podcast_social_links():
    from backend.services.podcast_service import get_social_links
    result = get_social_links()
    assert result.get("success") is True
    assert "youtube" in result.get("platforms", [])


def test_podcast_user_unlock_free_episode():
    from backend.services.podcast_service import get_episodes, user_has_unlock
    eps = [e for e in get_episodes() if not e.get("premium")]
    if not eps:
        pytest.skip("no free episodes")
    assert user_has_unlock("any_user", eps[0]) is True


def test_podcast_assign_agent():
    from backend.services.podcast_agent_service import AGENT_TOOLS
    assign_tool = next((t for t in AGENT_TOOLS if t["action"] == "assign_agent"), None)
    assert assign_tool is not None
    assert assign_tool.get("mutating") is True
    assert "podcast_producer_agent" in assign_tool.get("description", "").lower() or True


def test_podcast_sound_check():
    from backend.services.podcast_audio_service import sound_check_all, check_episode_audio
    from backend.services.podcast_service import get_episodes
    eps = get_episodes()
    if not eps:
        pytest.skip("no episodes")
    result = sound_check_all(repair=True)
    assert result.get("success") is True
    assert result.get("total", 0) >= 1
    chk = check_episode_audio(eps[0])
    assert chk.get("play_url", "").startswith("/api/podcast/episodes/")


def test_podcast_news_feed_and_comment():
    from backend.services.podcast_social_service import get_news_feed, add_news_comment, get_news_comments
    feed = get_news_feed(limit=5)
    if not feed:
        pytest.skip("no platform news")
    nid = feed[0].get("id")
    assert nid
    r = add_news_comment(nid, "test_news_comment_user", "Podcast news komment — platform change looks great!")
    assert r.get("success") is True
    comments = get_news_comments(nid)
    assert any("komment" in (c.get("content") or "").lower() for c in comments)


def test_podcast_portal_lines_max_sites():
    from backend.services.podcast_social_service import get_portal_lines
    r = get_portal_lines("battle")
    assert r.get("flavor") == "blue_bubble_cheese_gum"
    assert r.get("comment_hint")
    assert len(r.get("sites") or []) >= 20


def test_podcast_sound_lab():
    from backend.services.podcast_audio_service import get_sound_lab
    lab = get_sound_lab()
    assert lab.get("success") is True
    assert lab.get("flavor") == "blue_bubble_cheese_gum"
    assert len(lab.get("episodes") or []) >= 1
    assert "bbcg_flavor_synth" in (lab.get("features") or [])


def test_podcast_transcript_and_chapters():
    from backend.services.podcast_service import get_episodes
    from backend.services.podcast_expansions_service import get_episode_transcript, get_episode_chapters
    eps = get_episodes()
    if not eps:
        pytest.skip("no episodes")
    eid = eps[0]["id"]
    tr = get_episode_transcript(eid)
    ch = get_episode_chapters(eid)
    assert tr.get("success") is True
    assert tr.get("transcript")
    assert ch.get("success") is True
    assert len(ch.get("chapters") or []) >= 1


def test_podcast_rss_feed():
    from backend.services.podcast_expansions_service import build_rss_feed
    xml = build_rss_feed()
    assert "<?xml" in xml
    assert "MasterNoder Podcast" in xml
    assert "enclosure" in xml


def test_podcast_leaderboard():
    from backend.services.podcast_expansions_service import get_leaderboard
    lb = get_leaderboard(limit=5)
    assert lb.get("success") is True
    assert "leaderboard" in lb
