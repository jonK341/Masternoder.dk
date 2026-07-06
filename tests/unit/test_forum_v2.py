"""Tests for forum V2 upgrades: engine extensions + features service."""
import json
import os
import tempfile

import pytest


@pytest.fixture
def forum_v2(monkeypatch):
    td = tempfile.mkdtemp()
    paths = {
        "topics": os.path.join(td, "forum_topics.json"),
        "personas": os.path.join(td, "forum_personas.json"),
        "threads": os.path.join(td, "forum_threads.json"),
        "articles": os.path.join(td, "forum_articles.json"),
        "user_state": os.path.join(td, "forum_user_state.json"),
        "notifs": os.path.join(td, "forum_notifications.json"),
        "polls": os.path.join(td, "forum_polls.json"),
    }
    with open(paths["topics"], "w") as f:
        json.dump({"themes": [{"id": "th", "title": "Theme", "subforums": [
            {"id": "q", "title": "Q&A", "allows_questions": True}]}]}, f)
    with open(paths["personas"], "w") as f:
        json.dump({"personas": [
            {"id": "p1", "display_name": "Alice", "avatar": "🌟", "writing_style": "brief", "tone": "friendly"},
            {"id": "p2", "display_name": "Bob", "avatar": "🎮", "writing_style": "casual", "tone": "helpful"}]}, f)
    for k in ("threads",):
        with open(paths[k], "w") as f:
            json.dump({"threads": []}, f)
    with open(paths["articles"], "w") as f:
        json.dump({"articles": []}, f)

    import backend.services.forum_agent_service as svc
    import backend.services.forum_features_service as ff
    monkeypatch.setattr(svc, "_TOPICS_PATH", paths["topics"])
    monkeypatch.setattr(svc, "_PERSONAS_PATH", paths["personas"])
    monkeypatch.setattr(svc, "_THREADS_PATH", paths["threads"])
    monkeypatch.setattr(svc, "_ARTICLES_PATH", paths["articles"])
    monkeypatch.setattr(ff, "_USER_STATE_PATH", paths["user_state"])
    monkeypatch.setattr(ff, "_NOTIFS_PATH", paths["notifs"])
    monkeypatch.setattr(ff, "_POLLS_PATH", paths["polls"])
    return svc, ff


def test_slug_and_reading_time(forum_v2):
    svc, _ = forum_v2
    t = svc.create_thread(kind="question", title="How do I earn MN2 fast?", body="x " * 250, agent_authored=True)
    pub = svc.public_thread(t)
    assert pub["slug"] == "how-do-i-earn-mn2-fast"
    assert pub["reading_time_min"] >= 1
    assert pub["word_count"] >= 200


def test_downvotes_and_net(forum_v2):
    svc, _ = forum_v2
    t = svc.create_thread(kind="question", body="q?", agent_authored=True)
    tid = t["id"]
    assert svc.vote_thread(tid, "u1", 1)["net_votes"] == 1
    r = svc.vote_thread(tid, "u2", -1)
    assert r["downvotes"] == 1 and r["net_votes"] == 0
    # Same user flipping up -> down moves the vote
    r2 = svc.vote_thread(tid, "u1", -1)
    assert r2["votes"] == 0 and r2["downvotes"] == 2
    # Clear
    r3 = svc.vote_thread(tid, "u1", 0)
    assert r3["downvotes"] == 1


def test_edit_history_and_soft_delete(forum_v2):
    svc, _ = forum_v2
    t = svc.create_thread(kind="story", body="original body", agent_authored=True)
    pid = t["posts"][0]["id"]
    svc.edit_post(t["id"], pid, "updated body")
    hist = svc.post_history(t["id"], pid)
    assert hist and hist[0]["body"] == "original body"
    pub = svc.public_thread(t["id"] and [x for x in svc.load_threads() if x["id"] == t["id"]][0])
    assert pub["posts"][0]["edit_count"] == 1
    svc.delete_post(t["id"], pid, True)
    fresh = [x for x in svc.load_threads() if x["id"] == t["id"]][0]
    assert svc.public_thread(fresh)["posts"][0]["body"] == "[deleted]"


def test_similar_threads(forum_v2):
    svc, _ = forum_v2
    svc.create_thread(kind="question", title="How to stake MN2 tokens", body="a", agent_authored=True)
    dupes = svc.similar_threads("How to stake MN2 tokens quickly", limit=5)
    assert len(dupes) >= 1 and dupes[0]["similarity"] >= 0.35


def test_solved_sort(forum_v2):
    svc, _ = forum_v2
    t1 = svc.create_thread(kind="question", body="q1?", agent_authored=True)
    svc.create_thread(kind="question", body="q2?", agent_authored=True)
    reply = svc.reply_to_thread(t1["id"], agent_authored=True, body="answer")
    svc.accept_answer(t1["id"], reply["id"])
    solved, total = svc.list_threads_sorted(sort="solved", limit=10)
    assert total == 1 and solved[0]["id"] == t1["id"]
    unsolved, _ = svc.list_threads_sorted(sort="unsolved", limit=10)
    assert all(not x.get("solved") for x in unsolved)


def test_bookmarks_and_follows(forum_v2):
    svc, ff = forum_v2
    t = svc.create_thread(kind="question", body="q?", agent_authored=True)
    assert ff.toggle_bookmark("userX", t["id"])["bookmarked"] is True
    assert ff.toggle_bookmark("userX", t["id"])["bookmarked"] is False
    assert ff.toggle_follow("userX", t["id"])["following"] is True
    assert "userX" in ff.thread_followers(t["id"])


def test_notifications_flow(forum_v2):
    svc, ff = forum_v2
    t = svc.create_thread(kind="question", body="q?", agent_authored=True)
    ff.toggle_follow("watcher", t["id"])
    n = ff.notify_thread_followers(t["id"], actor="Bob", text="Bob replied", exclude="Bob")
    assert n == 1
    assert ff.unread_count("watcher") == 1
    ff.mark_notifications_read("watcher")
    assert ff.unread_count("watcher") == 0


def test_mentions_notify(forum_v2):
    svc, ff = forum_v2
    t = svc.create_thread(kind="question", body="q?", agent_authored=True)
    mentioned = ff.notify_mentions("thanks @alice and @bob", t["id"], actor="Carol")
    assert set(mentioned) == {"alice", "bob"}
    assert ff.unread_count("alice") == 1


def test_polls(forum_v2):
    svc, ff = forum_v2
    t = svc.create_thread(kind="question", body="which?", agent_authored=True)
    poll = ff.create_poll(t["id"], "Best asset?", ["MN2", "BTC", "ETH"])
    assert poll and len(poll["options"]) == 3
    oid = poll["options"][0]["id"]
    res = ff.vote_poll(t["id"], "voter1", oid)
    assert res["total_votes"] == 1 and res["your_vote"] == oid
    # Re-vote moves the vote, not adds
    oid2 = poll["options"][1]["id"]
    res2 = ff.vote_poll(t["id"], "voter1", oid2)
    assert res2["total_votes"] == 1 and res2["your_vote"] == oid2


def test_badges_and_level(forum_v2):
    svc, ff = forum_v2
    for _ in range(3):
        svc.create_thread(kind="story", body="a story", author_name="Nova")
    threads = svc.load_threads()
    badges = ff.compute_badges("Nova", threads)
    ids = {b["id"] for b in badges}
    assert "first_post" in ids and "author" in ids
    lvl = ff.reputation_level(160)
    assert lvl["level"] == "Trusted"


def test_saved_searches(forum_v2):
    svc, ff = forum_v2
    s = ff.save_search("u", "mn2 staking", {"sort": "hot"})
    assert s["q"] == "mn2 staking"
    assert len(ff.get_user_state("u")["saved_searches"]) == 1
    ff.delete_saved_search("u", s["id"])
    assert len(ff.get_user_state("u")["saved_searches"]) == 0


def test_tag_reputation(forum_v2):
    svc, ff = forum_v2
    svc.create_thread(kind="question", title="mn2 staking", body="stake mn2", author_name="Rex", tags=["mn2", "staking"])
    rep = svc.tag_reputation("Rex")
    assert rep.get("mn2", 0) >= 10
