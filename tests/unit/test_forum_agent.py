"""Tests for forum camouflage agent."""
import json
import os
import tempfile

import pytest
from flask import Flask


@pytest.fixture
def client(monkeypatch):
    from backend.routes.forum_routes import forum_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(forum_bp)
    return app.test_client()


@pytest.fixture
def forum_data_tmp(monkeypatch):
    td = tempfile.mkdtemp()
    topics = os.path.join(td, "forum_topics.json")
    personas = os.path.join(td, "forum_personas.json")
    threads = os.path.join(td, "forum_threads.json")
    articles = os.path.join(td, "forum_articles.json")

    with open(topics, "w", encoding="utf-8") as f:
        json.dump({
            "themes": [{
                "id": "test-theme",
                "title": "Test Theme",
                "subforums": [
                    {"id": "questions", "title": "Q&A", "allows_questions": True},
                    {"id": "stories", "title": "Stories", "allows_questions": False},
                ],
            }],
        }, f)
    with open(personas, "w", encoding="utf-8") as f:
        json.dump({
            "personas": [
                {"id": "p1", "display_name": "Alice", "avatar": "🌟", "writing_style": "brief", "tone": "friendly"},
                {"id": "p2", "display_name": "Bob", "avatar": "🎮", "writing_style": "casual", "tone": "helpful"},
            ],
        }, f)
    with open(threads, "w", encoding="utf-8") as f:
        json.dump({"threads": []}, f)
    with open(articles, "w", encoding="utf-8") as f:
        json.dump({"articles": []}, f)

    import backend.services.forum_agent_service as svc
    monkeypatch.setattr(svc, "_TOPICS_PATH", topics)
    monkeypatch.setattr(svc, "_PERSONAS_PATH", personas)
    monkeypatch.setattr(svc, "_THREADS_PATH", threads)
    monkeypatch.setattr(svc, "_ARTICLES_PATH", articles)
    yield svc


def test_create_thread_agent_authored(forum_data_tmp):
    svc = forum_data_tmp
    t = svc.create_thread(kind="question", agent_authored=True)
    assert t["agent_seeded"] is True
    assert len(t["posts"]) == 1
    pub = svc.public_thread(t)
    assert "agent_seeded" not in pub
    assert pub["posts"][0]["author_name"] in ("Alice", "Bob")


def test_reply_uses_different_persona(forum_data_tmp):
    svc = forum_data_tmp
    t = svc.create_thread(kind="question", agent_authored=True)
    author1 = t["posts"][0]["author_name"]
    post = svc.reply_to_thread(t["id"], agent_authored=True, body="Here is my answer.")
    assert post is not None
    assert post["author_name"] != author1 or len(svc.load_personas()) == 1


def test_run_agent_cycle(forum_data_tmp):
    svc = forum_data_tmp
    result = svc.run_agent_cycle(max_new_threads=2, max_replies=2)
    assert result.get("success")
    assert len(svc.load_threads()) >= 2


def test_forum_api_topics(client):
    r = client.get("/api/forum/topics")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"]
    assert len(data["themes"]) >= 1


def test_forum_api_threads_and_reply(client, forum_data_tmp):
    r = client.post("/api/forum/threads", json={
        "body": "How does MN2 staking work?",
        "kind": "question",
        "author_name": "TestUser",
        "topic_id": "test-theme",
        "subforum_id": "questions",
    })
    assert r.status_code == 201
    tid = r.get_json()["thread"]["id"]
    r2 = client.post(f"/api/forum/threads/{tid}/reply", json={
        "body": "Check explorer tab.",
        "author_name": "Helper",
    })
    assert r2.status_code == 201
    r3 = client.get(f"/api/forum/threads/{tid}")
    assert len(r3.get_json()["thread"]["posts"]) == 2


def test_thread_has_upgraded_fields(forum_data_tmp):
    svc = forum_data_tmp
    t = svc.create_thread(kind="question", body="How does MN2 staking reward work?", agent_authored=True)
    assert "tags" in t and "staking" in t["tags"]
    assert t["views"] == 0 and t["votes"] == 0
    assert t["pinned"] is False and t["locked"] is False and t["solved"] is False
    post = t["posts"][0]
    assert set(post["reactions"].keys()) == set(svc.REACTION_KEYS)


def test_vote_view_react_accept(forum_data_tmp):
    svc = forum_data_tmp
    t = svc.create_thread(kind="question", body="MN2 staking question?", agent_authored=True)
    tid = t["id"]
    assert svc.register_view(tid) == 1
    assert svc.register_view(tid) == 2
    v = svc.vote_thread(tid, "userA", 1)
    assert v["votes"] == 1 and v["voted"] is True
    # Duplicate vote from same user does not double count
    v2 = svc.vote_thread(tid, "userA", 1)
    assert v2["votes"] == 1
    reply = svc.reply_to_thread(tid, agent_authored=True, body="Try the wallet tab.")
    r = svc.react_to_post(tid, reply["id"], "helpful")
    assert r["reactions"]["helpful"] == 1
    acc = svc.accept_answer(tid, reply["id"])
    assert acc["solved"] is True and acc["accepted_post_id"] == reply["id"]
    fresh = [x for x in svc.load_threads() if x["id"] == tid][0]
    assert fresh["solved"] is True


def test_locked_thread_blocks_reply(forum_data_tmp):
    svc = forum_data_tmp
    t = svc.create_thread(kind="question", body="Locked topic?", agent_authored=True)
    svc.set_locked(t["id"], True)
    import pytest as _pt
    with _pt.raises(svc.ThreadLockedError):
        svc.reply_to_thread(t["id"], agent_authored=True, body="nope")


def test_search_sort_and_stats(forum_data_tmp):
    svc = forum_data_tmp
    svc.create_thread(kind="question", body="MN2 staking rewards guide", agent_authored=True)
    svc.create_thread(kind="story", body="A battle generator tale", agent_authored=True)
    threads, total = svc.list_threads_sorted(query="staking", sort="hot")
    assert total >= 1
    assert all("staking" in " ".join([p["body"] for p in t["posts"]]).lower()
               or "staking" in (t["title"] or "").lower() for t in threads)
    stats = svc.forum_stats()
    assert stats["threads"] >= 2
    cloud = svc.tag_cloud()
    assert isinstance(cloud, list)


def test_api_vote_react_search_stats(client, forum_data_tmp):
    r = client.post("/api/forum/threads", json={
        "body": "How do MN2 staking rewards accrue?",
        "kind": "question", "author_name": "Asker",
        "topic_id": "test-theme", "subforum_id": "questions",
    })
    tid = r.get_json()["thread"]["id"]
    rv = client.post(f"/api/forum/threads/{tid}/vote", json={"direction": 1, "user_id": "u9"})
    assert rv.status_code == 200 and rv.get_json()["votes"] == 1
    rr = client.post(f"/api/forum/threads/{tid}/reply", json={"body": "Via the wallet.", "author_name": "Ann"})
    pid = rr.get_json()["post"]["id"]
    rx = client.post(f"/api/forum/threads/{tid}/posts/{pid}/react", json={"reaction": "like"})
    assert rx.status_code == 200 and rx.get_json()["reactions"]["like"] == 1
    rs = client.get("/api/forum/search?q=staking")
    assert rs.status_code == 200 and rs.get_json()["success"]
    st = client.get("/api/forum/stats")
    assert st.get_json()["stats"]["threads"] >= 1
    tg = client.get("/api/forum/tags")
    assert tg.status_code == 200
    lb = client.get("/api/forum/leaderboard")
    assert lb.status_code == 200


def test_api_moderation_rejects_spam(client, forum_data_tmp):
    r = client.post("/api/forum/threads", json={
        "body": "free-crypto-giveaway click here", "kind": "question", "author_name": "Spammer",
    })
    assert r.status_code == 400


def test_api_languages(client):
    r = client.get("/api/forum/languages")
    assert r.status_code == 200
    codes = [l["code"] for l in r.get_json()["languages"]]
    assert "en" in codes and "da" in codes and "auto" in codes


def test_api_grammar_fallback(client):
    r = client.post("/api/forum/grammar", json={
        "text": "this  is a   test ,i has bad grammar.and no caps",
        "language": "en",
    })
    assert r.status_code == 200
    d = r.get_json()
    assert d["success"] and d["language"] == "en"
    # Fallback cleanup capitalizes and fixes spacing even without an LLM key.
    assert d["corrected"].startswith("This is a test")
    assert d["changed"] is True


def test_api_grammar_requires_text(client):
    r = client.post("/api/forum/grammar", json={"text": "  ", "language": "da"})
    assert r.status_code == 400


def test_api_social_networks_comprehensive(client):
    r = client.get("/api/forum/social-networks")
    assert r.status_code == 200
    d = r.get_json()
    ids = [n["id"] for n in d["networks"]]
    assert d["count"] >= 20
    for expected in ("x", "facebook", "linkedin", "reddit", "telegram", "discord",
                     "instagram", "tiktok", "youtube", "whatsapp", "mastodon", "bluesky"):
        assert expected in ids, expected
    assert {c["id"] for c in d["categories"]} >= {"social", "messaging", "community"}


def test_api_social_networks_category_filter(client):
    r = client.get("/api/forum/social-networks?category=community")
    ids = [n["id"] for n in r.get_json()["networks"]]
    assert "youtube" in ids and "discord" in ids
    assert "x" not in ids


def test_api_social_share_builds_url(client):
    r = client.post("/api/forum/share", json={
        "network": "reddit", "url": "https://example.com/x", "text": "Hello world",
    })
    assert r.status_code == 200
    d = r.get_json()
    assert d["success"] and "reddit.com/submit" in d["share_url"]
    assert "example.com" in d["share_url"] and "Hello%20world" in d["share_url"]


def test_api_social_share_unknown_network(client):
    r = client.post("/api/forum/share", json={"network": "nope"})
    assert r.status_code == 400
