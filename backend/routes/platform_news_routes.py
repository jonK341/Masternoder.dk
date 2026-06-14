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
