"""Social posts feed API and crypto reward hooks."""
import json
import tempfile
from pathlib import Path

import pytest
from flask import Flask


@pytest.fixture
def social_posts_app(monkeypatch):
    import backend.routes.social_routes as social_routes

    with tempfile.TemporaryDirectory(prefix="social_posts_") as temp_dir:
        base = Path(temp_dir)
        social_path = base / "social_structure.json"
        social_path.write_text(json.dumps(social_routes._default_social()), encoding="utf-8")

        monkeypatch.setattr(social_routes, "SOCIAL_DATA_PATH", str(social_path))
        monkeypatch.setattr(social_routes, "SOCIAL_NETWORKS_PATH", str(base / "missing_networks.json"))
        monkeypatch.setattr(social_routes, "_llm_moderate_post", lambda content, user_id: {"approved": True, "skipped": True})
        monkeypatch.setattr(
            social_routes,
            "_award_social_post_crypto",
            lambda user_id, action, reference, metadata=None: {
                "success": True,
                "action": action,
                "reference": reference,
            },
        )
        monkeypatch.setattr(social_routes, "push_activity", lambda *args, **kwargs: None)

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(social_routes.social_bp)
        yield app


def test_create_post_and_feed(social_posts_app):
    client = social_posts_app.test_client()

    create = client.post(
        "/api/social/posts",
        json={"user_id": "poster", "content": "Hello social feed!", "post_type": "text"},
    )
    assert create.status_code == 200
    body = create.get_json()
    assert body["success"] is True
    post_id = body["post"]["id"]
    assert post_id.startswith("post_")

    feed = client.get("/api/social/feed?user_id=reader&limit=10")
    payload = feed.get_json()
    assert payload["success"] is True
    assert len(payload["feed"]) == 1
    assert payload["feed"][0]["content"] == "Hello social feed!"
    assert payload["feed"][0]["likes_count"] == 0


def test_like_and_comment(social_posts_app):
    client = social_posts_app.test_client()

    create = client.post(
        "/api/social/posts",
        json={"user_id": "author", "content": "Like me", "post_type": "text"},
    )
    post_id = create.get_json()["post"]["id"]

    like = client.post(f"/api/social/posts/{post_id}/like", json={"user_id": "fan"})
    assert like.status_code == 200
    assert like.get_json()["action"] == "liked"
    assert like.get_json()["post"]["likes_count"] == 1

    comment = client.post(
        f"/api/social/posts/{post_id}/comment",
        json={"user_id": "fan", "comment": "Nice post"},
    )
    assert comment.status_code == 200
    assert comment.get_json()["comment"]["comment"] == "Nice post"

    feed = client.get("/api/social/feed?user_id=fan")
    row = feed.get_json()["feed"][0]
    assert row["comments_count"] == 1
    assert row["liked_by_me"] is True


def test_prefilter_blocks_unsafe_content(social_posts_app):
    client = social_posts_app.test_client()

    res = client.post(
        "/api/social/posts",
        json={"user_id": "bad", "content": "please kill yourself", "post_type": "text"},
    )
    assert res.status_code == 400
    assert "blocked" in res.get_json()["error"].lower()


def test_agent_recommendations_include_matches(social_posts_app):
    client = social_posts_app.test_client()

    client.post("/api/social/friends/add", json={"user_id": "u1", "friend_id": "u2"})
    client.post("/api/social/posts", json={"user_id": "u3", "content": "Third user post", "post_type": "text"})

    res = client.get("/api/social/agent/recommendations?user_id=u1")
    payload = res.get_json()
    assert payload["success"] is True
    assert "matches" in payload
    assert isinstance(payload["matches"], list)
    assert "earn_coach" in payload
    assert isinstance(payload["earn_coach"].get("tips"), list)


def test_earn_coach_llm_summary(social_posts_app, monkeypatch):
    client = social_posts_app.test_client()
    import backend.services.agent_ai_router as router_mod

    class _MockResp:
        success = True
        content = "Claim Signup Signal, then post with AI assist for routed_chat MN2."

    call_count = {"n": 0}

    def _fake_routed(messages, task_kind, user_id, **kwargs):
        call_count["n"] += 1
        return (
            _MockResp(),
            {"trace_id": "coach" + str(call_count["n"]), "crypto_reward": {"mn2_awarded": 0.002}},
        )

    monkeypatch.setattr(router_mod, "routed_chat", _fake_routed)

    res = client.get("/api/social/agent/recommendations?user_id=newbie&coach=1")
    body = res.get_json()
    assert body["success"] is True
    assert body["earn_coach"]["source"] == "llm"
    assert "Signup" in body["earn_coach"]["summary"] or "AI" in body["earn_coach"]["summary"]

    res2 = client.get("/api/social/agent/recommendations?user_id=newbie&coach=1")
    assert res2.get_json()["earn_coach"]["summary"] == body["earn_coach"]["summary"]
    assert call_count["n"] == 1

    res3 = client.get("/api/social/agent/recommendations?user_id=newbie&coach=1&refresh=1")
    assert res3.get_json()["earn_coach"]["source"] == "llm"
    assert call_count["n"] == 2


def test_referrals_promo(social_posts_app, monkeypatch):
    client = social_posts_app.test_client()
    import backend.routes.social_routes as social_routes
    import backend.services.agent_ai_router as router_mod

    networks_path = Path(social_routes.SOCIAL_DATA_PATH).parent / "test_networks.json"
    networks_path.write_text(
        json.dumps({
            "networks": [
                {
                    "id": "x",
                    "name": "X",
                    "icon": "X",
                    "color": "#000",
                    "share_url": "https://twitter.com/intent/tweet?text={text}&url={url}",
                }
            ],
            "default_share_text": "Join MasterNoder",
            "default_share_hashtags": "MN2",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(social_routes, "SOCIAL_NETWORKS_PATH", str(networks_path))

    class _MockResp:
        success = True
        content = "Play Hunters Game with me on MasterNoder! https://masternoder.dk/game?ref=MN-TEST"

    monkeypatch.setattr(
        router_mod,
        "routed_chat",
        lambda messages, task_kind, user_id, **kwargs: (
            _MockResp(),
            {"trace_id": "promo1", "crypto_reward": {"mn2_awarded": 0.002}},
        ),
    )

    res = client.post("/api/social/referrals/promo", json={"user_id": "promoter"})
    body = res.get_json()
    assert res.status_code == 200
    assert body["success"] is True
    assert "MasterNoder" in body["promo_text"]
    assert body["referral_code"].startswith("MN-")
    assert len(body.get("share_links") or []) == 1
    assert body.get("reward", {}).get("mn2_awarded") == 0.002


def test_task_kinds_include_social_ai_mapping():
    from backend.services.agent_ai_router import TASK_KIND_ENDPOINTS, TASK_ROUTING_TABLE

    for kind in (
        "social_ai_draft",
        "feed_rank",
        "earn_coach",
        "referral_content",
        "moderation_check",
        "friend_match_hint",
    ):
        assert kind in TASK_ROUTING_TABLE
        assert kind in TASK_KIND_ENDPOINTS


def test_ranked_feed_uses_llm_cache(social_posts_app, monkeypatch):
    client = social_posts_app.test_client()
    import backend.routes.social_routes as social_routes

    order_calls = {"n": 0}

    class _MockResp:
        success = True
        content = ""

    def _fake_routed(messages, task_kind, user_id, **kwargs):
        order_calls["n"] += 1
        return _MockResp(), {"trace_id": f"t{order_calls['n']}"}

    monkeypatch.setattr(social_routes, "_llm_feed_rank", lambda posts, uid: posts)

    client.post("/api/social/posts", json={"user_id": "a", "content": "Post A", "post_type": "text"})
    client.post("/api/social/posts", json={"user_id": "b", "content": "Post B", "post_type": "text"})

    r1 = client.get("/api/social/feed?user_id=reader&ranked=1")
    r2 = client.get("/api/social/feed?user_id=reader&ranked=1")
    assert r1.get_json()["ranked"] is True
    assert r2.get_json()["success"] is True


def test_social_posts_ai_draft(social_posts_app, monkeypatch):
    client = social_posts_app.test_client()

    class _MockResp:
        success = True
        content = "Just hit a new high score in Hunters Game on MasterNoder!"

    import backend.services.agent_ai_router as router_mod

    monkeypatch.setattr(
        router_mod,
        "routed_chat",
        lambda messages, task_kind, user_id, **kwargs: (
            _MockResp(),
            {"trace_id": "draft1", "crypto_reward": {"mn2_awarded": 0.002, "coins_awarded": 5}},
        ),
    )

    res = client.post(
        "/api/social/posts/ai-draft",
        json={"user_id": "poster", "hint": "Hunters Game win"},
    )
    body = res.get_json()
    assert res.status_code == 200
    assert body["success"] is True
    assert "Hunters Game" in body["draft"]
    assert body.get("reward", {}).get("mn2_awarded") == 0.002


def test_social_posts_ai_draft_tone(social_posts_app, monkeypatch):
    client = social_posts_app.test_client()
    captured = {}

    class _MockResp:
        success = True
        content = "Who else is grinding Hunters Game tonight?"

    import backend.services.agent_ai_router as router_mod

    def _fake_routed(messages, task_kind, user_id, **kwargs):
        captured["messages"] = messages
        return _MockResp(), {"trace_id": "draft_tone", "crypto_reward": {"mn2_awarded": 0.002}}

    monkeypatch.setattr(router_mod, "routed_chat", _fake_routed)

    res = client.post(
        "/api/social/posts/ai-draft",
        json={"user_id": "poster", "hint": "Hunters Game", "tone": "question"},
    )
    body = res.get_json()
    assert res.status_code == 200
    assert body["success"] is True
    assert body["tone"] == "question"
    system = captured["messages"][0]["content"]
    user = captured["messages"][1]["content"]
    assert "question" in system.lower()
    assert "Tone: question" in user

    res_invalid = client.post(
        "/api/social/posts/ai-draft",
        json={"user_id": "poster", "tone": "invalid_tone"},
    )
    assert res_invalid.get_json()["tone"] == "casual"


def test_social_chat_ai_reply(social_posts_app, monkeypatch):
    client = social_posts_app.test_client()

    class _MockResp:
        success = True
        content = "Welcome to social chat!"

    import backend.services.agent_ai_router as router_mod

    monkeypatch.setattr(
        router_mod,
        "routed_chat",
        lambda messages, task_kind, user_id, **kwargs: (
            _MockResp(),
            {"trace_id": "chat1", "crypto_reward": {"mn2_awarded": 0.002}},
        ),
    )

    res = client.post(
        "/api/social/chat/send",
        json={"user_id": "chatter", "message": "Hello room", "ai_reply": True},
    )
    body = res.get_json()
    assert body["success"] is True
    assert body.get("ai_reply", {}).get("message") == "Welcome to social chat!"
    assert body.get("reward", {}).get("mn2_awarded") == 0.002


def test_social_chat_messages_list_stability(social_posts_app):
    """GET /api/social/chat/messages — stable shape for smart-poll clients."""
    client = social_posts_app.test_client()

    empty = client.get("/api/social/chat/messages?limit=30")
    assert empty.status_code == 200
    body = empty.get_json()
    assert body["success"] is True
    assert body["messages"] == []
    assert body["count"] == 0

    client.post(
        "/api/social/chat/send",
        json={"user_id": "alice", "message": "Hello room"},
    )
    client.post(
        "/api/social/chat/send",
        json={"user_id": "bob", "message": "Hi Alice"},
    )

    listed = client.get("/api/social/chat/messages?limit=30")
    payload = listed.get_json()
    assert payload["success"] is True
    assert payload["count"] == 2
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["message"] == "Hello room"
    assert payload["messages"][0]["display_name"]
    assert payload["messages"][1]["message"] == "Hi Alice"

    capped = client.get("/api/social/chat/messages?limit=1")
    capped_body = capped.get_json()
    assert capped_body["success"] is True
    assert capped_body["count"] == 1
    assert len(capped_body["messages"]) == 1
    assert capped_body["messages"][0]["message"] == "Hi Alice"


def test_llm_feed_rank_cache(social_posts_app, monkeypatch):
    import backend.routes.social_routes as social_routes

    social_routes._FEED_RANK_CACHE.clear()
    calls = {"n": 0}

    class _MockResp:
        success = True
        content = '{"order": ["post_b", "post_a"]}'

    def _fake_routed(messages, task_kind, user_id, **kwargs):
        calls["n"] += 1
        return _MockResp(), {"trace_id": "rank1"}

    import backend.services.agent_ai_router as router_mod

    monkeypatch.setattr(router_mod, "routed_chat", _fake_routed)

    posts = [
        {"id": "post_a", "user_id": "a", "content": "A", "likes": [], "comments": []},
        {"id": "post_b", "user_id": "b", "content": "B", "likes": ["x"], "comments": []},
    ]
    ranked1 = social_routes._llm_feed_rank(posts, "reader")
    ranked2 = social_routes._llm_feed_rank(posts, "reader")
    assert [p["id"] for p in ranked1[:2]] == ["post_b", "post_a"]
    assert calls["n"] == 1
    assert ranked1[0]["id"] == ranked2[0]["id"]
