"""
Platform news feed — curated MasterNoder announcements for home and /news.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any, Dict, List, Set
from xml.sax.saxutils import escape as xml_escape

from flask import Blueprint, Response, jsonify, request

platform_news_bp = Blueprint("platform_news", __name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_NEWS_PATH = os.path.join(_BASE_DIR, "data", "platform_news.json")
_SUBS_PATH = os.path.join(_BASE_DIR, "data", "platform_news_subscribers.json")

# Canonical multi-channel taxonomy (Phase 5).
KNOWN_CHANNELS = (
    "home",
    "explorer",
    "casino",
    "generator",
    "game",
    "market",
    "agents",
    "discord",
    "ops",
    "platform",
    "podcast",
)


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


def _item_channels(item: dict) -> Set[str]:
    chans: Set[str] = set()
    raw_list = item.get("channels")
    if isinstance(raw_list, list):
        for c in raw_list:
            s = str(c or "").strip().lower()
            if s:
                chans.add(s)
    for key in ("channel", "category"):
        s = str(item.get(key) or "").strip().lower()
        if s:
            chans.add(s)
    return chans


def _load_subscriber_counts() -> Dict[str, int]:
    """Optional file: {\"home\": 12, \"casino\": 3, ...} or {\"channels\": {...}}."""
    if not os.path.isfile(_SUBS_PATH):
        return {}
    try:
        with open(_SUBS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("channels"), dict):
            data = data["channels"]
        if not isinstance(data, dict):
            return {}
        out: Dict[str, int] = {}
        for k, v in data.items():
            try:
                out[str(k).strip().lower()] = max(0, int(v))
            except (TypeError, ValueError):
                continue
        return out
    except Exception:
        return {}


def _ops_ok() -> bool:
    secret = (
        os.environ.get("MN2_OPS_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("ADMIN_OPS_SECRET")
        or ""
    ).strip()
    provided = (
        request.headers.get("X-Ops-Secret")
        or request.args.get("ops_secret")
        or request.args.get("token")
        or ""
    ).strip()
    if not secret:
        return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")
    return bool(provided) and provided == secret


@platform_news_bp.route("/api/news/platform", methods=["GET"])
def platform_news():
    try:
        limit = request.args.get("limit", 10, type=int)
        featured_only = request.args.get("featured", "").lower() in ("1", "true", "yes")
        channel = (request.args.get("channel") or "").strip().lower()
        items = _load_news()
        if channel:
            items = [i for i in items if channel in _item_channels(i)]
        if featured_only:
            items = [i for i in items if i.get("featured")]
        if limit > 0:
            items = items[:limit]
        return jsonify({
            "success": True,
            "news": items,
            "count": len(items),
            "channel": channel or None,
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "news": []}), 500


@platform_news_bp.route("/api/news/channels", methods=["GET"])
def platform_news_channels():
    """Channel list with post counts + optional subscriber counts."""
    items = _load_news()
    counts: Counter = Counter()
    for item in items:
        chans = _item_channels(item)
        if not chans:
            counts["home"] += 1
        else:
            for ch in chans:
                counts[ch] += 1
    subs = _load_subscriber_counts()
    # Prefer known taxonomy order, then any extras from data.
    ordered: List[str] = []
    for ch in KNOWN_CHANNELS:
        if ch in counts or ch in subs:
            ordered.append(ch)
    for ch in sorted(counts.keys()):
        if ch not in ordered:
            ordered.append(ch)
    for ch in sorted(subs.keys()):
        if ch not in ordered:
            ordered.append(ch)
    channels = [
        {
            "id": ch,
            "count": int(counts.get(ch, 0)),
            "subscribers": int(subs.get(ch, 0)),
        }
        for ch in ordered
    ]
    return jsonify({
        "success": True,
        "channels": channels,
        "known": list(KNOWN_CHANNELS),
        "total_items": len(items),
    }), 200


@platform_news_bp.route("/api/news/publish", methods=["POST"])
def platform_news_publish_route():
    """Ops-only publish into platform_news.json; optional Discord fan-out."""
    if not _ops_ok():
        return jsonify({"success": False, "error": "admin_required"}), 403
    body = request.get_json(silent=True) or {}
    from backend.services.platform_news_publish import publish

    channels = body.get("channels")
    channel = body.get("channel") or "ops"
    if isinstance(channels, list) and channels:
        channel = str(channels[0] or channel)
    result = publish(
        item_id=body.get("id") or body.get("item_id") or "manual",
        title=body.get("title") or "Update",
        summary=body.get("summary") or "",
        channel=str(channel),
        href=body.get("href") or "/",
        featured=bool(body.get("featured")),
        channels=channels if isinstance(channels, list) else None,
    )
    if body.get("discord") and result.get("success"):
        try:
            from backend.services.discord_service import post_message
            item = result.get("item") or {}
            post_message(
                item.get("channel") or "ops",
                {"title": item.get("title"), "description": item.get("summary")},
            )
            result["discord_queued"] = True
        except Exception as exc:
            result["discord_queued"] = False
            result["discord_error"] = str(exc)[:200]
    return jsonify(result), 200 if result.get("success") else 400


@platform_news_bp.route("/api/news/rss", methods=["GET"])
@platform_news_bp.route("/api/news/rss/<channel>", methods=["GET"])
def platform_news_rss(channel: str = ""):
    """Simple RSS feed for a channel (or all items when channel omitted)."""
    channel = (channel or request.args.get("channel") or "").strip().lower()
    items = _load_news()
    if channel:
        items = [i for i in items if channel in _item_channels(i)]
    items = items[:50]
    title = f"MasterNoder news — {channel}" if channel else "MasterNoder news"
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        f"<title>{xml_escape(title)}</title>",
        "<link>/</link>",
        f"<description>{xml_escape(title)}</description>",
    ]
    for item in items:
        link = str(item.get("href") or "/")
        parts.append("<item>")
        parts.append(f"<title>{xml_escape(str(item.get('title') or 'Update'))}</title>")
        parts.append(f"<link>{xml_escape(link)}</link>")
        parts.append(f"<guid isPermaLink=\"false\">{xml_escape(str(item.get('id') or link))}</guid>")
        parts.append(f"<pubDate>{xml_escape(str(item.get('date') or ''))}</pubDate>")
        parts.append(f"<description>{xml_escape(str(item.get('summary') or ''))}</description>")
        parts.append("</item>")
    parts.append("</channel></rss>")
    return Response("\n".join(parts), mimetype="application/rss+xml; charset=utf-8")
