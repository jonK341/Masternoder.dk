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


@forum_bp.route("/api/forum/overview", methods=["GET"])
def forum_overview():
    """Hub metadata for Forum UI tabs."""
    articles = _load_articles()
    news = _load_json(_PLATFORM_NEWS_PATH, {"items": []}).get("items") or []
    try:
        from backend.services.forum_agent_service import load_threads
        thread_count = len(load_threads())
    except Exception:
        thread_count = 0
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
            "threads": thread_count,
        },
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
    from backend.services.forum_agent_service import load_threads, public_thread
    topic_id = (request.args.get("topic_id") or "").strip()
    subforum_id = (request.args.get("subforum_id") or "").strip()
    limit = request.args.get("limit", 40, type=int)
    threads = load_threads()
    if topic_id:
        threads = [t for t in threads if t.get("topic_id") == topic_id]
    if subforum_id:
        threads = [t for t in threads if t.get("subforum_id") == subforum_id]
    threads = sorted(threads, key=lambda t: t.get("updated_at") or "", reverse=True)
    if limit > 0:
        threads = threads[:limit]
    return jsonify({
        "success": True,
        "threads": [public_thread(t) for t in threads],
        "count": len(threads),
    }), 200


@forum_bp.route("/api/forum/threads", methods=["POST"])
def forum_create_thread():
    from backend.services.forum_agent_service import create_thread, public_thread
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip() or None
    content = (body.get("body") or "").strip() or None
    kind = (body.get("kind") or "question").strip()[:20]
    author_name = (body.get("author_name") or _resolve_uid()).strip()[:80]
    thread = create_thread(
        topic_id=body.get("topic_id"),
        subforum_id=body.get("subforum_id"),
        kind=kind,
        title=title,
        body=content,
        author_name=author_name,
        agent_authored=False,
    )
    return jsonify({"success": True, "thread": public_thread(thread)}), 201


@forum_bp.route("/api/forum/threads/<thread_id>", methods=["GET"])
def forum_get_thread(thread_id: str):
    from backend.services.forum_agent_service import load_threads, public_thread
    for t in load_threads():
        if t.get("id") == thread_id:
            return jsonify({"success": True, "thread": public_thread(t)}), 200
    return jsonify({"success": False, "error": "not found"}), 404


@forum_bp.route("/api/forum/threads/<thread_id>/reply", methods=["POST"])
def forum_reply_thread(thread_id: str):
    from backend.services.forum_agent_service import reply_to_thread, public_thread, load_threads
    body = request.get_json(silent=True) or {}
    content = (body.get("body") or "").strip() or None
    kind = (body.get("kind") or "answer").strip()[:20]
    author_name = (body.get("author_name") or _resolve_uid()).strip()[:80]
    post = reply_to_thread(
        thread_id,
        body=content,
        kind=kind,
        author_name=author_name,
        agent_authored=False,
    )
    if not post:
        return jsonify({"success": False, "error": "thread not found"}), 404
    thread = next((t for t in load_threads() if t.get("id") == thread_id), None)
    return jsonify({"success": True, "post": post, "thread": public_thread(thread) if thread else None}), 201


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
    return jsonify({"success": True, "personas": personas, "count": len(personas)}), 200


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


@forum_bp.route("/api/forum/social-networks", methods=["GET"])
def forum_social_networks():
    """Share targets including Discord, Facebook, Instagram, Snapchat."""
    base = _load_json(_SOCIAL_NETWORKS_PATH, {})
    extra = [
        {
            "id": "discord",
            "name": "Discord",
            "icon": "💬",
            "color": "#5865F2",
            "share_url": "https://discord.com/channels/@me",
            "content_url": "/api/discord/link",
            "encode_text": False,
        },
        {
            "id": "instagram",
            "name": "Instagram",
            "icon": "📷",
            "color": "#E4405F",
            "share_url": "https://www.instagram.com/",
            "encode_text": False,
        },
        {
            "id": "snapchat",
            "name": "Snapchat",
            "icon": "👻",
            "color": "#FFFC00",
            "share_url": "https://www.snapchat.com/scan?attachmentUrl={url}",
            "encode_text": False,
        },
    ]
    networks = list(base.get("networks") or []) + extra
    return jsonify({
        "success": True,
        "networks": networks,
        "default_share_text": base.get("default_share_text"),
        "integrations": {
            "discord_api": "/api/discord/link",
            "facebook_oauth": "/api/auth/facebook/start",
            "podcast_channels": "/api/podcast/channels",
        },
    }), 200


@forum_bp.route("/api/forum/share", methods=["POST"])
def forum_share():
    """Build share URL for article or news item."""
    body = request.get_json(silent=True) or {}
    network_id = (body.get("network") or "").strip().lower()
    text = (body.get("text") or "Check out MasterNoder Forum").strip()
    url = (body.get("url") or request.host_url.rstrip("/") + "/forum/").strip()
    resp = forum_social_networks()
    networks = resp[0].get_json().get("networks") or []
    net = next((n for n in networks if n.get("id") == network_id), None)
    if not net:
        return jsonify({"success": False, "error": "unknown network"}), 400
    from urllib.parse import quote
    share_tpl = net.get("share_url") or ""
    share_url = share_tpl.replace("{url}", quote(url, safe=""))
    if "{text}" in share_tpl:
        share_url = share_url.replace("{text}", quote(text, safe=""))
    return jsonify({"success": True, "share_url": share_url, "network": network_id}), 200


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
