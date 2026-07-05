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
