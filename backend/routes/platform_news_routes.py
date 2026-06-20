"""
Platform news feed — curated MasterNoder announcements for home and /news.
"""
import json
import os
from flask import Blueprint, jsonify, request

platform_news_bp = Blueprint("platform_news", __name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_NEWS_PATH = os.path.join(_BASE_DIR, "data", "platform_news.json")


def _load_news() -> list:
    if not os.path.exists(_NEWS_PATH):
        return []
    try:
        with open(_NEWS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items") or []
        return sorted(items, key=lambda x: x.get("date") or "", reverse=True)
    except Exception:
        return []


@platform_news_bp.route("/api/news/platform", methods=["GET"])
def platform_news():
    try:
        limit = request.args.get("limit", 10, type=int)
        featured_only = request.args.get("featured", "").lower() in ("1", "true", "yes")
        channel = (request.args.get("channel") or "").strip().lower()
        items = _load_news()
        if channel:
            items = [
                i for i in items
                if (i.get("channel") or i.get("category") or "").lower() == channel
            ]
        if featured_only:
            items = [i for i in items if i.get("featured")]
        if limit > 0:
            items = items[:limit]
        return jsonify({"success": True, "news": items, "count": len(items), "channel": channel or None}), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "news": []}), 500


@platform_news_bp.route("/api/news/channels", methods=["GET"])
def platform_news_channels():
    items = _load_news()
    counts: dict = {}
    for item in items:
        ch = (item.get("channel") or item.get("category") or "home").lower()
        counts[ch] = counts.get(ch, 0) + 1
    channels = [{"id": k, "count": v} for k, v in sorted(counts.items())]
    return jsonify({"success": True, "channels": channels}), 200


@platform_news_bp.route("/api/news/publish", methods=["POST"])
def platform_news_publish():
    import os
    secret = os.environ.get("DISCORD_OPS_SECRET") or os.environ.get("ADMIN_OPS_SECRET", "")
    if secret and request.headers.get("X-Ops-Secret") != secret:
        if request.environ.get("REMOTE_ADDR") not in ("127.0.0.1", "::1"):
            return jsonify({"success": False, "error": "admin_required"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.platform_news_publish import publish
    result = publish(
        item_id=body.get("id") or body.get("item_id") or "manual",
        title=body.get("title") or "Update",
        summary=body.get("summary") or "",
        channel=body.get("channel") or "ops",
        href=body.get("href") or "/",
        featured=bool(body.get("featured")),
    )
    if body.get("discord") and result.get("success"):
        try:
            from backend.services.discord_service import post_message
            post_message(result["item"].get("channel", "ops"), {"title": result["item"]["title"], "description": result["item"]["summary"]})
        except Exception:
            pass
    return jsonify(result), 200 if result.get("success") else 400
