"""
Unified Forum hub — news, articles, chat, rulebooks, docs, support, social share, Wikipedia.
"""
import json
import os
import uuid
from datetime import datetime, timezone

import requests
from flask import Blueprint, jsonify, request

forum_bp = Blueprint("forum", __name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ARTICLES_PATH = os.path.join(_BASE_DIR, "data", "forum_articles.json")
_RULES_PATH = os.path.join(_BASE_DIR, "data", "forum_rules.json")
_PARAGRAPHS_PATH = os.path.join(_BASE_DIR, "data", "rights_law_paragraphs.json")
_PLATFORM_NEWS_PATH = os.path.join(_BASE_DIR, "data", "platform_news.json")
_SOCIAL_NETWORKS_PATH = os.path.join(_BASE_DIR, "data", "social_networks.json")


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        body = request.get_json(silent=True) or {}
        return body.get("user_id") or request.args.get("user_id") or "default_user"


def _load_json(path: str, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_articles() -> list:
    data = _load_json(_ARTICLES_PATH, {"articles": []})
    return data.get("articles") or []


def _save_articles(articles: list) -> None:
    _save_json(_ARTICLES_PATH, {"articles": articles, "$schema": "masternoder.forum_articles.v1"})


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# --- Lightweight in-memory rate limiter (per-IP, per-action) --------------
_RATE_BUCKET: dict = {}


def _rate_limited(action: str, limit: int = 12, window_s: int = 60) -> bool:
    import time
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "anon").split(",")[0].strip()
    key = f"{action}:{ip}"
    now = time.time()
    hits = [t for t in _RATE_BUCKET.get(key, []) if now - t < window_s]
    if len(hits) >= limit:
        _RATE_BUCKET[key] = hits
        return True
    hits.append(now)
    _RATE_BUCKET[key] = hits
    return False


_BANNED_WORDS = {"viagra", "casino-spam", "free-crypto-giveaway", "porn", "click-here-now"}


def _moderate(text: str) -> tuple:
    """Return (ok, cleaned). Rejects obvious spam, trims control chars."""
    if not text:
        return True, ""
    low = text.lower()
    for w in _BANNED_WORDS:
        if w in low:
            return False, text
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return True, cleaned.strip()


@forum_bp.route("/api/forum/overview", methods=["GET"])
def forum_overview():
    """Hub metadata for Forum UI tabs."""
    articles = _load_articles()
    news = _load_json(_PLATFORM_NEWS_PATH, {"items": []}).get("items") or []
    try:
        from backend.services.forum_agent_service import forum_stats
        stats = forum_stats()
    except Exception:
        stats = {"threads": 0}
    return jsonify({
        "success": True,
        "tabs": [
            {"id": "home", "label": "Home", "icon": "🏠"},
            {"id": "discussions", "label": "Discussions", "icon": "💭"},
            {"id": "news", "label": "News", "icon": "📰"},
            {"id": "articles", "label": "Articles", "icon": "✍️"},
            {"id": "chat", "label": "Chat", "icon": "💬"},
            {"id": "podcast", "label": "Podcast", "icon": "🎙️"},
            {"id": "rulebooks", "label": "Rulebooks", "icon": "📖"},
            {"id": "paragraphs", "label": "Paragraphs", "icon": "§"},
            {"id": "docs", "label": "Docs", "icon": "📚"},
            {"id": "support", "label": "Support", "icon": "🛠️"},
            {"id": "social", "label": "Social", "icon": "🌐"},
            {"id": "wikipedia", "label": "Wikipedia", "icon": "🔍"},
        ],
        "counts": {
            "articles": len(articles),
            "news": len(news),
            "threads": stats.get("threads", 0),
        },
        "stats": stats,
        "discussions_url": "/api/forum/threads",
        "topics_url": "/api/forum/topics",
        "writing_rules_url": "/api/forum/rules",
    }), 200


@forum_bp.route("/api/forum/topics", methods=["GET"])
def forum_topics():
    from backend.services.forum_agent_service import load_topics
    themes = load_topics()
    return jsonify({"success": True, "themes": themes, "count": len(themes)}), 200


@forum_bp.route("/api/forum/threads", methods=["GET"])
def forum_list_threads():
    from backend.services.forum_agent_service import list_threads_sorted, public_thread
    topic_id = (request.args.get("topic_id") or "").strip()
    subforum_id = (request.args.get("subforum_id") or "").strip()
    tag = (request.args.get("tag") or "").strip()
    kind = (request.args.get("kind") or "").strip()
    sort = (request.args.get("sort") or "new").strip().lower()
    query = (request.args.get("q") or "").strip()
    offset = max(0, request.args.get("offset", 0, type=int))
    limit = request.args.get("limit", 20, type=int)
    threads, total = list_threads_sorted(
        topic_id=topic_id, subforum_id=subforum_id, tag=tag, kind=kind,
        sort=sort, query=query, offset=offset, limit=limit,
    )
    return jsonify({
        "success": True,
        "threads": [public_thread(t, detail=False) for t in threads],
        "count": len(threads),
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(threads) < total,
        "sort": sort,
    }), 200


@forum_bp.route("/api/forum/threads", methods=["POST"])
def forum_create_thread():
    from backend.services.forum_agent_service import create_thread, public_thread
    if _rate_limited("create_thread", limit=8, window_s=60):
        return jsonify({"success": False, "error": "rate limited — slow down"}), 429
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip() or None
    content = (body.get("body") or "").strip() or None
    if not content:
        return jsonify({"success": False, "error": "body required"}), 400
    if len(content) > 50000:
        return jsonify({"success": False, "error": "body too long (max 50000)"}), 400
    ok, content = _moderate(content)
    if not ok:
        return jsonify({"success": False, "error": "content rejected by moderation"}), 400
    kind = (body.get("kind") or "question").strip()[:20]
    author_name = (body.get("author_name") or _resolve_uid()).strip()[:80]
    tags = body.get("tags") if isinstance(body.get("tags"), list) else None
    # Merge inline #hashtags into tags.
    from backend.services import forum_features_service as ff
    hashtags = ff.extract_hashtags(f"{title or ''} {content}")
    if hashtags:
        tags = list(dict.fromkeys((tags or []) + hashtags))
    thread = create_thread(
        topic_id=body.get("topic_id"),
        subforum_id=body.get("subforum_id"),
        kind=kind,
        title=title,
        body=content,
        author_name=author_name,
        agent_authored=False,
        tags=tags,
    )
    # Follower/mention notifications + optional poll.
    ff.notify_mentions(content, thread.get("id"), actor=author_name,
                       post_id=(thread.get("posts") or [{}])[0].get("id", ""))
    poll = body.get("poll") or {}
    if isinstance(poll, dict) and poll.get("options"):
        ff.create_poll(thread.get("id"), poll.get("question", title or ""), poll.get("options"))
    return jsonify({"success": True, "thread": public_thread(thread)}), 201


@forum_bp.route("/api/forum/threads/<thread_id>", methods=["GET"])
def forum_get_thread(thread_id: str):
    from backend.services.forum_agent_service import (
        load_threads, public_thread, register_view, related_threads,
    )
    if request.args.get("count_view", "1") != "0":
        register_view(thread_id)
    from backend.services import forum_features_service as ff
    uid = _resolve_uid()
    for t in load_threads():
        if t.get("id") == thread_id:
            related = [public_thread(r, detail=False) for r in related_threads(thread_id)]
            ff.mark_read(uid, thread_id)
            return jsonify({
                "success": True,
                "thread": public_thread(t, float_accepted=True),
                "related": related,
                "poll": ff.get_poll(thread_id, uid),
                "bookmarked": thread_id in (ff.get_user_state(uid).get("bookmarks") or []),
                "following": thread_id in (ff.get_user_state(uid).get("follows") or []),
            }), 200
    return jsonify({"success": False, "error": "not found"}), 404


@forum_bp.route("/api/forum/threads/<thread_id>/reply", methods=["POST"])
def forum_reply_thread(thread_id: str):
    from backend.services.forum_agent_service import (
        reply_to_thread, public_thread, load_threads, ThreadLockedError,
    )
    if _rate_limited("reply", limit=20, window_s=60):
        return jsonify({"success": False, "error": "rate limited — slow down"}), 429
    body = request.get_json(silent=True) or {}
    content = (body.get("body") or "").strip() or None
    if not content:
        return jsonify({"success": False, "error": "body required"}), 400
    ok, content = _moderate(content)
    if not ok:
        return jsonify({"success": False, "error": "content rejected by moderation"}), 400
    kind = (body.get("kind") or "answer").strip()[:20]
    author_name = (body.get("author_name") or _resolve_uid()).strip()[:80]
    try:
        post = reply_to_thread(
            thread_id,
            body=content,
            kind=kind,
            author_name=author_name,
            agent_authored=False,
        )
    except ThreadLockedError:
        return jsonify({"success": False, "error": "thread is locked"}), 423
    if not post:
        return jsonify({"success": False, "error": "thread not found"}), 404
    thread = next((t for t in load_threads() if t.get("id") == thread_id), None)
    # Notify thread followers and any @mentioned users; auto-follow on reply.
    from backend.services import forum_features_service as ff
    snippet = (content or "")[:120]
    ff.notify_thread_followers(thread_id, actor=author_name, text=f"{author_name} replied: {snippet}",
                               exclude=author_name, post_id=post.get("id"), ntype="reply")
    ff.notify_mentions(content, thread_id, actor=author_name, post_id=post.get("id"))
    return jsonify({"success": True, "post": post, "thread": public_thread(thread) if thread else None}), 201


@forum_bp.route("/api/forum/threads/<thread_id>/vote", methods=["POST"])
def forum_vote_thread(thread_id: str):
    from backend.services.forum_agent_service import vote_thread
    if _rate_limited("vote", limit=40, window_s=60):
        return jsonify({"success": False, "error": "rate limited"}), 429
    body = request.get_json(silent=True) or {}
    direction = int(body.get("direction", 1))
    result = vote_thread(thread_id, voter=_resolve_uid(), direction=direction)
    if result is None:
        return jsonify({"success": False, "error": "thread not found"}), 404
    return jsonify({"success": True, **result}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/posts/<post_id>/react", methods=["POST"])
def forum_react_post(thread_id: str, post_id: str):
    from backend.services.forum_agent_service import react_to_post
    if _rate_limited("react", limit=60, window_s=60):
        return jsonify({"success": False, "error": "rate limited"}), 429
    body = request.get_json(silent=True) or {}
    reaction = (body.get("reaction") or "like").strip().lower()
    result = react_to_post(thread_id, post_id, reaction)
    if result is None:
        return jsonify({"success": False, "error": "invalid reaction or not found"}), 400
    return jsonify({"success": True, **result}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/accept", methods=["POST"])
def forum_accept_answer(thread_id: str):
    from backend.services.forum_agent_service import accept_answer
    body = request.get_json(silent=True) or {}
    post_id = (body.get("post_id") or "").strip()
    result = accept_answer(thread_id, post_id)
    if result is None:
        return jsonify({"success": False, "error": "post not found"}), 404
    return jsonify({"success": True, **result}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/posts/<post_id>", methods=["PATCH"])
def forum_edit_post(thread_id: str, post_id: str):
    from backend.services.forum_agent_service import edit_post
    body = request.get_json(silent=True) or {}
    new_body = (body.get("body") or "").strip()
    if not new_body:
        return jsonify({"success": False, "error": "body required"}), 400
    ok, new_body = _moderate(new_body)
    if not ok:
        return jsonify({"success": False, "error": "content rejected"}), 400
    result = edit_post(thread_id, post_id, new_body)
    if result is None:
        return jsonify({"success": False, "error": "post not found"}), 404
    return jsonify({"success": True, **result}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/moderate", methods=["POST"])
def forum_moderate_thread(thread_id: str):
    """Pin/lock/tag — requires AGENT_CRON_SECRET when set."""
    from backend.services.forum_agent_service import set_pinned, set_locked, set_thread_tags
    secret = (os.environ.get("AGENT_CRON_SECRET") or "").strip()
    tok = (request.headers.get("X-Agent-Cron-Token") or request.args.get("token") or "").strip()
    if secret and tok != secret:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    out = {}
    if "pinned" in body:
        r = set_pinned(thread_id, bool(body["pinned"]))
        if r:
            out.update(r)
    if "locked" in body:
        r = set_locked(thread_id, bool(body["locked"]))
        if r:
            out.update(r)
    if isinstance(body.get("tags"), list):
        r = set_thread_tags(thread_id, body["tags"])
        if r:
            out.update(r)
    if not out:
        return jsonify({"success": False, "error": "nothing to update or thread not found"}), 400
    return jsonify({"success": True, **out}), 200


@forum_bp.route("/api/forum/search", methods=["GET"])
def forum_search():
    """Search threads + articles."""
    from backend.services.forum_agent_service import list_threads_sorted, public_thread
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"success": False, "error": "q required"}), 400
    limit = request.args.get("limit", 20, type=int)
    threads, total = list_threads_sorted(query=q, sort="hot", limit=limit)
    articles = [
        a for a in _load_articles()
        if q.lower() in (a.get("title") or "").lower()
        or q.lower() in (a.get("body_markdown") or "").lower()
    ][:limit]
    return jsonify({
        "success": True,
        "query": q,
        "threads": [public_thread(t, detail=False) for t in threads],
        "articles": articles,
        "thread_total": total,
        "counts": {"threads": len(threads), "articles": len(articles)},
    }), 200


@forum_bp.route("/api/forum/tags", methods=["GET"])
def forum_tags():
    from backend.services.forum_agent_service import tag_cloud
    tags = tag_cloud()
    return jsonify({"success": True, "tags": tags, "count": len(tags)}), 200


@forum_bp.route("/api/forum/trending", methods=["GET"])
def forum_trending():
    from backend.services.forum_agent_service import trending_threads, public_thread
    limit = request.args.get("limit", 5, type=int)
    threads = trending_threads(limit=limit)
    return jsonify({
        "success": True,
        "threads": [public_thread(t, detail=False) for t in threads],
    }), 200


@forum_bp.route("/api/forum/stats", methods=["GET"])
def forum_stats_route():
    from backend.services.forum_agent_service import forum_stats
    return jsonify({"success": True, "stats": forum_stats()}), 200


@forum_bp.route("/api/forum/leaderboard", methods=["GET"])
def forum_leaderboard():
    from backend.services.forum_agent_service import leaderboard
    limit = request.args.get("limit", 10, type=int)
    return jsonify({"success": True, "leaderboard": leaderboard(limit=limit)}), 200


# ===========================================================================
# V2: personalization, notifications, polls, badges, discovery
# ===========================================================================
@forum_bp.route("/api/forum/me", methods=["GET"])
def forum_me():
    """Current user's forum state: bookmarks, follows, unread notifications."""
    from backend.services import forum_features_service as ff
    uid = _resolve_uid()
    ff.touch_last_seen(uid)
    st = ff.get_user_state(uid)
    st["unread_notifications"] = ff.unread_count(uid)
    return jsonify({"success": True, "me": st}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/bookmark", methods=["POST"])
def forum_bookmark(thread_id: str):
    from backend.services import forum_features_service as ff
    return jsonify({"success": True, **ff.toggle_bookmark(_resolve_uid(), thread_id)}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/follow", methods=["POST"])
def forum_follow(thread_id: str):
    from backend.services import forum_features_service as ff
    return jsonify({"success": True, **ff.toggle_follow(_resolve_uid(), thread_id)}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/read", methods=["POST"])
def forum_mark_read(thread_id: str):
    from backend.services import forum_features_service as ff
    return jsonify({"success": True, **ff.mark_read(_resolve_uid(), thread_id)}), 200


@forum_bp.route("/api/forum/tags/<tag>/follow", methods=["POST"])
def forum_follow_tag(tag: str):
    from backend.services import forum_features_service as ff
    return jsonify({"success": True, **ff.toggle_tag_follow(_resolve_uid(), tag)}), 200


@forum_bp.route("/api/forum/bookmarks", methods=["GET"])
def forum_bookmarks():
    from backend.services import forum_features_service as ff
    from backend.services.forum_agent_service import list_threads_sorted, public_thread
    uid = _resolve_uid()
    ids = ff.get_user_state(uid).get("bookmarks") or []
    threads, total = list_threads_sorted(ids=ids, sort="new", limit=100)
    return jsonify({"success": True, "threads": [public_thread(t, detail=False) for t in threads], "total": total}), 200


@forum_bp.route("/api/forum/following", methods=["GET"])
def forum_following():
    from backend.services import forum_features_service as ff
    from backend.services.forum_agent_service import list_threads_sorted, public_thread
    uid = _resolve_uid()
    ids = ff.get_user_state(uid).get("follows") or []
    threads, total = list_threads_sorted(ids=ids, sort="new", limit=100)
    return jsonify({"success": True, "threads": [public_thread(t, detail=False) for t in threads], "total": total}), 200


@forum_bp.route("/api/forum/notifications", methods=["GET"])
def forum_notifications():
    from backend.services import forum_features_service as ff
    uid = _resolve_uid()
    only_unread = request.args.get("unread") == "1"
    return jsonify({
        "success": True,
        "notifications": ff.list_notifications(uid, only_unread=only_unread, limit=request.args.get("limit", 50, type=int)),
        "unread": ff.unread_count(uid),
    }), 200


@forum_bp.route("/api/forum/notifications/read", methods=["POST"])
def forum_notifications_read():
    from backend.services import forum_features_service as ff
    body = request.get_json(silent=True) or {}
    ids = body.get("ids") if isinstance(body.get("ids"), list) else None
    return jsonify({"success": True, **ff.mark_notifications_read(_resolve_uid(), ids)}), 200


@forum_bp.route("/api/forum/saved-searches", methods=["GET", "POST"])
def forum_saved_searches():
    from backend.services import forum_features_service as ff
    uid = _resolve_uid()
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        q = (body.get("q") or "").strip()
        if not q:
            return jsonify({"success": False, "error": "q required"}), 400
        return jsonify({"success": True, "search": ff.save_search(uid, q, body.get("filters"))}), 201
    return jsonify({"success": True, "searches": ff.get_user_state(uid).get("saved_searches") or []}), 200


@forum_bp.route("/api/forum/saved-searches/<search_id>", methods=["DELETE"])
def forum_delete_saved_search(search_id: str):
    from backend.services import forum_features_service as ff
    return jsonify({"success": True, **ff.delete_saved_search(_resolve_uid(), search_id)}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/poll", methods=["GET", "POST"])
def forum_poll(thread_id: str):
    from backend.services import forum_features_service as ff
    uid = _resolve_uid()
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        poll = ff.create_poll(thread_id, body.get("question", ""), body.get("options") or [],
                              closes_in_hours=int(body.get("closes_in_hours", 168)))
        if not poll:
            return jsonify({"success": False, "error": "need a question and >=2 options"}), 400
        return jsonify({"success": True, "poll": ff.get_poll(thread_id, uid)}), 201
    poll = ff.get_poll(thread_id, uid)
    if not poll:
        return jsonify({"success": False, "error": "no poll"}), 404
    return jsonify({"success": True, "poll": poll}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/poll/vote", methods=["POST"])
def forum_poll_vote(thread_id: str):
    from backend.services import forum_features_service as ff
    if _rate_limited("poll_vote", limit=30, window_s=60):
        return jsonify({"success": False, "error": "rate limited"}), 429
    body = request.get_json(silent=True) or {}
    res = ff.vote_poll(thread_id, _resolve_uid(), (body.get("option_id") or "").strip())
    if res is None:
        return jsonify({"success": False, "error": "no poll"}), 404
    if res.get("error"):
        return jsonify({"success": False, "error": res["error"]}), 400
    return jsonify({"success": True, "poll": res}), 200


@forum_bp.route("/api/forum/threads/similar", methods=["GET"])
def forum_similar():
    """Duplicate/related detection by title — used by the composer."""
    from backend.services.forum_agent_service import similar_threads
    title = (request.args.get("title") or "").strip()
    if len(title) < 6:
        return jsonify({"success": True, "threads": []}), 200
    return jsonify({"success": True, "threads": similar_threads(title, limit=request.args.get("limit", 5, type=int))}), 200


@forum_bp.route("/api/forum/authors/<author_name>", methods=["GET"])
def forum_author_profile(author_name: str):
    """Public author profile: stats, badges, level, per-tag reputation, recent threads."""
    from backend.services.forum_agent_service import (
        load_threads, threads_by_author, public_thread, tag_reputation, leaderboard,
    )
    from backend.services import forum_features_service as ff
    threads = load_threads()
    stats = ff.author_stats(author_name, threads)
    rep = stats["threads"] * 10 + stats["replies"] * 5 + stats["reactions"] * 2 + stats["accepted"] * 25
    recent = [public_thread(t, detail=False) for t in threads_by_author(author_name, limit=10)]
    return jsonify({
        "success": True,
        "author": {
            "author_name": author_name,
            "stats": stats,
            "reputation": rep,
            "level": ff.reputation_level(rep),
            "badges": ff.compute_badges(author_name, threads),
            "tag_reputation": tag_reputation(author_name),
            "recent_threads": recent,
        },
    }), 200


@forum_bp.route("/api/forum/threads/<thread_id>/posts/<post_id>/delete", methods=["POST"])
def forum_delete_post(thread_id: str, post_id: str):
    from backend.services.forum_agent_service import delete_post
    body = request.get_json(silent=True) or {}
    res = delete_post(thread_id, post_id, bool(body.get("deleted", True)))
    if res is None:
        return jsonify({"success": False, "error": "post not found"}), 404
    return jsonify({"success": True, **res}), 200


@forum_bp.route("/api/forum/threads/<thread_id>/posts/<post_id>/history", methods=["GET"])
def forum_post_history(thread_id: str, post_id: str):
    from backend.services.forum_agent_service import post_history
    hist = post_history(thread_id, post_id)
    if hist is None:
        return jsonify({"success": False, "error": "post not found"}), 404
    return jsonify({"success": True, "history": hist}), 200


@forum_bp.route("/api/forum/digest", methods=["GET"])
def forum_digest():
    """Personalized digest: new threads, replies on followed threads, unread notifications."""
    from backend.services import forum_features_service as ff
    from backend.services.forum_agent_service import list_threads_sorted, public_thread
    uid = _resolve_uid()
    st = ff.get_user_state(uid)
    follows = st.get("follows") or []
    tag_follows = st.get("tag_follows") or []
    new_threads, _ = list_threads_sorted(sort="new", limit=8)
    followed, _ = list_threads_sorted(ids=follows, sort="new", limit=10) if follows else ([], 0)
    tag_threads = []
    for tg in tag_follows[:5]:
        tt, _ = list_threads_sorted(tag=tg, sort="new", limit=3)
        tag_threads.extend(tt)
    return jsonify({
        "success": True,
        "digest": {
            "new_threads": [public_thread(t, detail=False) for t in new_threads],
            "followed_updates": [public_thread(t, detail=False) for t in followed],
            "tag_updates": [public_thread(t, detail=False) for t in tag_threads[:8]],
            "unread_notifications": ff.unread_count(uid),
        },
    }), 200


@forum_bp.route("/api/forum/report", methods=["POST"])
def forum_report():
    """Flag a thread/post for review — appended to a moderation log."""
    if _rate_limited("report", limit=10, window_s=60):
        return jsonify({"success": False, "error": "rate limited"}), 429
    body = request.get_json(silent=True) or {}
    entry = {
        "at": _iso_now(),
        "reporter": _resolve_uid(),
        "thread_id": (body.get("thread_id") or "").strip()[:64],
        "post_id": (body.get("post_id") or "").strip()[:64],
        "reason": (body.get("reason") or "").strip()[:280],
    }
    if not entry["thread_id"]:
        return jsonify({"success": False, "error": "thread_id required"}), 400
    log_dir = os.path.join(_BASE_DIR, "logs", "forum")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "reports.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return jsonify({"success": True, "reported": True}), 201


@forum_bp.route("/api/forum/rss", methods=["GET"])
def forum_rss():
    """Minimal RSS 2.0 feed of latest threads + articles."""
    from backend.services.forum_agent_service import list_threads_sorted, public_thread
    from xml.sax.saxutils import escape
    threads, _ = list_threads_sorted(sort="new", limit=25)
    base = request.host_url.rstrip("/")
    items = []
    for t in threads:
        pt = public_thread(t, detail=False)
        link = f"{base}/forum#discussions/{pt.get('id')}"
        items.append(
            f"<item><title>{escape(pt.get('title') or 'Thread')}</title>"
            f"<link>{escape(link)}</link>"
            f"<description>{escape(pt.get('excerpt') or '')}</description>"
            f"<pubDate>{escape(pt.get('updated_at') or '')}</pubDate>"
            f"<guid isPermaLink=\"false\">{escape(pt.get('id') or '')}</guid></item>"
        )
    for a in _load_articles()[:15]:
        link = f"{base}/forum#articles/{a.get('slug') or a.get('id')}"
        items.append(
            f"<item><title>{escape(a.get('title') or 'Article')}</title>"
            f"<link>{escape(link)}</link>"
            f"<description>{escape(a.get('summary') or '')}</description>"
            f"<guid isPermaLink=\"false\">{escape(a.get('id') or '')}</guid></item>"
        )
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        "<title>MasterNoder Forum</title>"
        f"<link>{escape(base)}/forum/</link>"
        "<description>Latest forum discussions and articles</description>"
        + "".join(items) +
        "</channel></rss>"
    )
    return rss, 200, {"Content-Type": "application/rss+xml; charset=utf-8"}


@forum_bp.route("/api/forum/agent/run", methods=["POST"])
def forum_agent_run():
    """Run camouflage agent cycle (requires AGENT_CRON_SECRET when set)."""
    import os
    secret = (os.environ.get("AGENT_CRON_SECRET") or "").strip()
    tok = (request.headers.get("X-Agent-Cron-Token") or request.args.get("token") or "").strip()
    if secret and tok != secret:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    body = request.get_json(silent=True) or {}
    max_threads = int(body.get("max_new_threads") or request.args.get("max_new_threads") or 2)
    max_replies = int(body.get("max_replies") or request.args.get("max_replies") or 3)
    from backend.services.forum_agent_service import run_agent_cycle
    result = run_agent_cycle(max_new_threads=max_threads, max_replies=max_replies)
    return jsonify({"success": result.get("success", True), **result}), 200


@forum_bp.route("/api/forum/agent/seed", methods=["POST"])
def forum_agent_seed():
    """Bootstrap initial forum threads if empty."""
    import os
    secret = (os.environ.get("AGENT_CRON_SECRET") or "").strip()
    tok = (request.headers.get("X-Agent-Cron-Token") or request.args.get("token") or "").strip()
    if secret and tok != secret:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    from backend.services.forum_agent_service import seed_initial_content
    return jsonify(seed_initial_content()), 200


@forum_bp.route("/api/forum/personas", methods=["GET"])
def forum_personas_public():
    """Public persona list (camouflage — no agent flags)."""
    from backend.services.forum_agent_service import load_personas, public_persona
    personas = [public_persona(p) for p in load_personas()]
    personas.sort(key=lambda p: p.get("reputation", 0), reverse=True)
    return jsonify({"success": True, "personas": personas, "count": len(personas)}), 200


@forum_bp.route("/api/forum/personas/<persona_id>", methods=["GET"])
def forum_persona_detail(persona_id: str):
    """Public member profile with their recent threads."""
    from backend.services.forum_agent_service import (
        load_personas, public_persona, threads_by_author, public_thread,
    )
    p = next((x for x in load_personas() if x.get("id") == persona_id), None)
    if not p:
        return jsonify({"success": False, "error": "not found"}), 404
    pub = public_persona(p)
    threads = threads_by_author(p.get("display_name"))
    return jsonify({
        "success": True,
        "persona": pub,
        "threads": [public_thread(t, detail=False) for t in threads],
    }), 200


@forum_bp.route("/api/forum/rules", methods=["GET"])
def forum_rules():
    data = _load_json(_RULES_PATH, {"sections": []})
    return jsonify({"success": True, **data}), 200


@forum_bp.route("/api/forum/paragraphs", methods=["GET"])
def forum_paragraphs():
    data = _load_json(_PARAGRAPHS_PATH, {"paragraphs": []})
    return jsonify({"success": True, **data}), 200


@forum_bp.route("/api/forum/news", methods=["GET"])
def forum_unified_news():
    """Platform news + optional channel filter."""
    limit = request.args.get("limit", 30, type=int)
    channel = (request.args.get("channel") or "").strip().lower()
    items = _load_json(_PLATFORM_NEWS_PATH, {"items": []}).get("items") or []
    items = sorted(items, key=lambda x: x.get("date") or "", reverse=True)
    if channel:
        items = [
            i for i in items
            if (i.get("channel") or i.get("category") or "").lower() == channel
        ]
    podcast_items = [i for i in items if (i.get("channel") or "").lower() == "podcast"]
    return jsonify({
        "success": True,
        "news": items[:limit] if limit > 0 else items,
        "count": len(items),
        "sources": ["platform", "podcast", "profit-daemon"],
        "podcast_highlight_count": len(podcast_items),
    }), 200


@forum_bp.route("/api/forum/articles", methods=["GET"])
def list_articles():
    limit = request.args.get("limit", 50, type=int)
    category = (request.args.get("category") or "").strip().lower()
    articles = _load_articles()
    articles = sorted(articles, key=lambda a: a.get("created_at") or "", reverse=True)
    if category:
        articles = [a for a in articles if (a.get("category") or "").lower() == category]
    if limit > 0:
        articles = articles[:limit]
    return jsonify({"success": True, "articles": articles, "count": len(articles)}), 200


@forum_bp.route("/api/forum/articles", methods=["POST"])
def create_article():
    """User-written forum article."""
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    content = (body.get("body") or body.get("body_markdown") or "").strip()
    if not title or not content:
        return jsonify({"success": False, "error": "title and body required"}), 400
    if len(title) > 200:
        return jsonify({"success": False, "error": "title too long (max 200)"}), 400
    if len(content) > 50000:
        return jsonify({"success": False, "error": "body too long (max 50000)"}), 400

    uid = _resolve_uid()
    author_name = (body.get("author_name") or uid).strip()[:80]
    article_id = str(uuid.uuid4())
    now = _iso_now()
    article = {
        "id": article_id,
        "slug": body.get("slug") or article_id[:8],
        "title": title,
        "author_id": uid,
        "author_name": author_name,
        "category": (body.get("category") or "general").strip()[:40],
        "featured": False,
        "created_at": now,
        "updated_at": now,
        "summary": (body.get("summary") or content[:240]).strip(),
        "body_markdown": content,
    }
    articles = _load_articles()
    articles.insert(0, article)
    _save_articles(articles)

    try:
        from backend.routes.social_routes import push_activity
        push_activity(uid, "forum_article", f"Published: {title}", {"article_id": article_id})
    except Exception:
        pass

    return jsonify({"success": True, "article": article}), 201


@forum_bp.route("/api/forum/articles/<article_id>", methods=["GET"])
def get_article(article_id: str):
    for a in _load_articles():
        if a.get("id") == article_id or a.get("slug") == article_id:
            return jsonify({"success": True, "article": a}), 200
    return jsonify({"success": False, "error": "not found"}), 404


@forum_bp.route("/api/forum/feed", methods=["GET"])
def forum_feed():
    """Mixed feed: threads, articles + recent news headlines."""
    limit = request.args.get("limit", 25, type=int)
    from backend.services.forum_agent_service import load_threads, public_thread
    threads = load_threads()[:10]
    articles = _load_articles()[:limit]
    news = (_load_json(_PLATFORM_NEWS_PATH, {"items": []}).get("items") or [])[:10]
    feed = []
    for t in threads:
        pt = public_thread(t)
        opening = (pt.get("posts") or [{}])[0]
        feed.append({
            "type": "thread",
            "id": pt.get("id"),
            "title": pt.get("title"),
            "summary": (opening.get("body") or "")[:200],
            "author_name": opening.get("author_name"),
            "theme_title": pt.get("theme_title"),
            "created_at": pt.get("updated_at"),
            "href": f"/forum#discussions/{pt.get('id')}",
        })
    for a in articles:
        feed.append({
            "type": "article",
            "id": a.get("id"),
            "title": a.get("title"),
            "summary": a.get("summary"),
            "author_name": a.get("author_name"),
            "created_at": a.get("created_at"),
            "href": f"/forum#articles/{a.get('slug') or a.get('id')}",
        })
    for n in news:
        feed.append({
            "type": "news",
            "id": n.get("id"),
            "title": n.get("title"),
            "summary": n.get("summary"),
            "channel": n.get("channel"),
            "created_at": n.get("date"),
            "href": n.get("href") or "/forum#news",
        })
    feed.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return jsonify({"success": True, "feed": feed[:limit], "count": len(feed)}), 200


# Built-in fallback used only if data/social_networks.json is missing/corrupt.
_SOCIAL_FALLBACK = {
    "default_share_text": "MasterNoder — AI video, game, battle & community forum",
    "categories": [
        {"id": "social", "label": "Social"},
        {"id": "messaging", "label": "Messaging"},
        {"id": "community", "label": "Community & video"},
        {"id": "save", "label": "Save & bookmark"},
    ],
    "networks": [
        {"id": "x", "name": "X (Twitter)", "icon": "𝕏", "color": "#000000", "category": "social", "type": "share",
         "share_url": "https://twitter.com/intent/tweet?text={text}&url={url}", "encode_text": True},
        {"id": "facebook", "name": "Facebook", "icon": "f", "color": "#1877f2", "category": "social", "type": "share",
         "share_url": "https://www.facebook.com/sharer/sharer.php?u={url}", "encode_text": False},
        {"id": "linkedin", "name": "LinkedIn", "icon": "in", "color": "#0a66c2", "category": "social", "type": "share",
         "share_url": "https://www.linkedin.com/sharing/share-offsite/?url={url}", "encode_text": False},
        {"id": "whatsapp", "name": "WhatsApp", "icon": "💬", "color": "#25d366", "category": "messaging", "type": "share",
         "share_url": "https://wa.me/?text={text}%20{url}", "encode_text": True},
    ],
}


@forum_bp.route("/api/forum/social-networks", methods=["GET"])
def forum_social_networks():
    """Comprehensive share/follow targets, grouped by category (from data file)."""
    data = _load_json(_SOCIAL_NETWORKS_PATH, {})
    networks = data.get("networks")
    if not networks:
        data = _SOCIAL_FALLBACK
        networks = data["networks"]
    category = (request.args.get("category") or "").strip().lower()
    if category:
        networks = [n for n in networks if (n.get("category") or "").lower() == category]
    return jsonify({
        "success": True,
        "networks": networks,
        "count": len(networks),
        "categories": data.get("categories") or _SOCIAL_FALLBACK["categories"],
        "default_share_text": data.get("default_share_text") or _SOCIAL_FALLBACK["default_share_text"],
        "integrations": {
            "discord_api": "/api/discord/link",
            "facebook_oauth": "/api/auth/facebook/start",
            "podcast_channels": "/api/podcast/channels",
        },
    }), 200


def _all_social_networks() -> list:
    data = _load_json(_SOCIAL_NETWORKS_PATH, {})
    return data.get("networks") or _SOCIAL_FALLBACK["networks"]


@forum_bp.route("/api/forum/share", methods=["POST"])
def forum_share():
    """Build share URL for article or news item."""
    body = request.get_json(silent=True) or {}
    network_id = (body.get("network") or "").strip().lower()
    text = (body.get("text") or "Check out MasterNoder Forum").strip()
    url = (body.get("url") or request.host_url.rstrip("/") + "/forum/").strip()
    net = next((n for n in _all_social_networks() if n.get("id") == network_id), None)
    if not net:
        return jsonify({"success": False, "error": "unknown network"}), 400
    from urllib.parse import quote
    share_tpl = net.get("share_url") or ""
    share_url = share_tpl.replace("{url}", quote(url, safe=""))
    if "{text}" in share_tpl:
        share_url = share_url.replace("{text}", quote(text, safe=""))
    return jsonify({
        "success": True,
        "share_url": share_url,
        "network": network_id,
        "type": net.get("type", "share"),
    }), 200


# ---------------------------------------------------------------------------
# Multi-language grammar assistant ("Grammarly" per language)
# ---------------------------------------------------------------------------
_SUPPORTED_LANGUAGES = [
    {"code": "auto", "name": "Auto-detect", "native": "Auto", "flag": "🌐"},
    {"code": "en", "name": "English", "native": "English", "flag": "🇬🇧"},
    {"code": "da", "name": "Danish", "native": "Dansk", "flag": "🇩🇰"},
    {"code": "de", "name": "German", "native": "Deutsch", "flag": "🇩🇪"},
    {"code": "es", "name": "Spanish", "native": "Español", "flag": "🇪🇸"},
    {"code": "fr", "name": "French", "native": "Français", "flag": "🇫🇷"},
    {"code": "it", "name": "Italian", "native": "Italiano", "flag": "🇮🇹"},
    {"code": "pt", "name": "Portuguese", "native": "Português", "flag": "🇵🇹"},
    {"code": "nl", "name": "Dutch", "native": "Nederlands", "flag": "🇳🇱"},
    {"code": "sv", "name": "Swedish", "native": "Svenska", "flag": "🇸🇪"},
    {"code": "nb", "name": "Norwegian", "native": "Norsk", "flag": "🇳🇴"},
    {"code": "fi", "name": "Finnish", "native": "Suomi", "flag": "🇫🇮"},
    {"code": "pl", "name": "Polish", "native": "Polski", "flag": "🇵🇱"},
    {"code": "tr", "name": "Turkish", "native": "Türkçe", "flag": "🇹🇷"},
    {"code": "ru", "name": "Russian", "native": "Русский", "flag": "🇷🇺"},
    {"code": "uk", "name": "Ukrainian", "native": "Українська", "flag": "🇺🇦"},
    {"code": "ar", "name": "Arabic", "native": "العربية", "flag": "🇸🇦"},
    {"code": "hi", "name": "Hindi", "native": "हिन्दी", "flag": "🇮🇳"},
    {"code": "zh", "name": "Chinese", "native": "中文", "flag": "🇨🇳"},
    {"code": "ja", "name": "Japanese", "native": "日本語", "flag": "🇯🇵"},
    {"code": "ko", "name": "Korean", "native": "한국어", "flag": "🇰🇷"},
]
_LANG_BY_CODE = {l["code"]: l for l in _SUPPORTED_LANGUAGES}


def _basic_grammar_cleanup(text: str) -> str:
    """Offline fallback: whitespace, spacing and simple capitalization tidy-up."""
    import re
    t = re.sub(r"[ \t]+", " ", text.strip())
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)          # no space before punctuation
    t = re.sub(r"([,.;:!?])(?=[^\s\d])", r"\1 ", t)   # space after punctuation
    t = re.sub(r"\n{3,}", "\n\n", t)
    # Capitalize first letter of each sentence
    parts = re.split(r"([.!?]\s+)", t)
    out = []
    for i, p in enumerate(parts):
        if i % 2 == 0 and p:
            p = p[0].upper() + p[1:]
        out.append(p)
    return "".join(out)


@forum_bp.route("/api/forum/languages", methods=["GET"])
def forum_languages():
    """Supported languages for the per-language grammar assistant."""
    return jsonify({"success": True, "languages": _SUPPORTED_LANGUAGES}), 200


@forum_bp.route("/api/forum/grammar", methods=["POST"])
def forum_grammar():
    """Language-aware grammar / spelling assistant for forum writing.

    Body: {text, language} where language is a code from /api/forum/languages.
    Returns corrected text in the same language, preserving meaning and tone.
    """
    if _rate_limited("grammar", limit=20, window_s=60):
        return jsonify({"success": False, "error": "rate limited — slow down"}), 429
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    lang_code = (body.get("language") or "auto").strip().lower()
    if not text:
        return jsonify({"success": False, "error": "text required"}), 400
    if len(text) > 8000:
        return jsonify({"success": False, "error": "text too long (max 8000)"}), 400
    lang = _LANG_BY_CODE.get(lang_code, _LANG_BY_CODE["auto"])
    lang_name = lang["name"]

    corrected = None
    engine = "fallback"
    try:
        from backend.services.llm_service import chat
        if lang_code == "auto":
            lang_instr = (
                "First detect the language of the text, then correct it IN THAT SAME LANGUAGE. "
                "Never translate to another language."
            )
        else:
            lang_instr = (
                f"The text is written in {lang_name}. Correct it in {lang_name}. "
                "Never translate to another language."
            )
        system = (
            "You are a meticulous multilingual proofreader (like Grammarly). "
            "Fix spelling, grammar, punctuation, and clumsy phrasing while preserving the "
            "author's meaning, tone, and formatting. " + lang_instr + " "
            "Return ONLY the corrected text with no preamble, quotes, or commentary."
        )
        resp = chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=1200,
            task_type="default",
        )
        if resp.success and resp.content:
            corrected = resp.content.strip().strip('"')
            engine = "llm"
    except Exception:
        corrected = None

    if not corrected:
        corrected = _basic_grammar_cleanup(text)
        engine = "fallback"

    changed = corrected.strip() != text.strip()
    return jsonify({
        "success": True,
        "language": lang_code,
        "language_name": lang_name,
        "engine": engine,
        "original": text,
        "corrected": corrected,
        "changed": changed,
        "note": ("Suggestions ready" if changed else "Looks good — no changes needed"),
    }), 200


@forum_bp.route("/api/forum/wikipedia", methods=["GET"])
def forum_wikipedia():
    """Wikipedia REST summary proxy for research posts."""
    title = (request.args.get("title") or request.args.get("q") or "").strip()
    if not title:
        return jsonify({"success": False, "error": "title or q required"}), 400
    title_enc = title.replace(" ", "_")
    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title_enc}",
            timeout=8,
            headers={"User-Agent": "MasterNoderForum/1.0 (https://masternoder.dk; contact@platform)"},
        )
        if r.status_code == 404:
            return jsonify({"success": False, "error": "page not found"}), 404
        r.raise_for_status()
        data = r.json()
        return jsonify({
            "success": True,
            "title": data.get("title"),
            "extract": data.get("extract"),
            "description": data.get("description"),
            "content_urls": data.get("content_urls"),
            "thumbnail": (data.get("thumbnail") or {}).get("source"),
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 502


@forum_bp.route("/api/forum/rulebooks/index", methods=["GET"])
def forum_rulebooks_index():
    """Proxy to rulebook index for Forum rulebooks tab."""
    try:
        from backend.routes.rulebook_routes import get_rulebook_index
        return get_rulebook_index()
    except Exception:
        index = _load_json(os.path.join(_BASE_DIR, "data", "rulebook_index_v15.json"), {})
        return jsonify({"success": True, "index": index}), 200


@forum_bp.route("/api/forum/docs", methods=["GET"])
def forum_docs():
    """Curated documentation links for Forum docs tab."""
    return jsonify({
        "success": True,
        "docs": [
            {"title": "Site structure", "href": "/forum#articles/master-guide-all-pages", "source": "forum"},
            {"title": "Time & achievement guides", "href": "/game#guides", "source": "game"},
            {"title": "Hunters walkthroughs", "href": "/game#walkthrough", "source": "game"},
            {"title": "Agent Support resources", "href": "/api/agent/support/resources", "source": "api"},
            {"title": "Compendium calm library", "href": "/compendium/?calm=1", "source": "compendium"},
            {"title": "Lab overview", "href": "/api/lab/overview", "source": "api"},
        ],
    }), 200
