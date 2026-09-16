"""Podcast social — episode comments, likes, channel follows, activity feed."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SOCIAL_FILE = os.path.join(_BASE, "data", "podcast_social.json")
_MAX_COMMENTS = 500
_MAX_ACTIVITY = 200


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_social() -> dict:
    if not os.path.isfile(_SOCIAL_FILE):
        return {"comments": {}, "likes": {}, "follows": {}, "activity": []}
    try:
        with open(_SOCIAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {"comments": {}, "likes": {}, "follows": {}, "activity": []}


def _write_social(data: dict) -> None:
    os.makedirs(os.path.dirname(_SOCIAL_FILE), exist_ok=True)
    tmp = _SOCIAL_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _SOCIAL_FILE)


def _push_activity(data: dict, record: dict) -> None:
    activity = list(data.get("activity") or [])
    activity.insert(0, record)
    data["activity"] = activity[:_MAX_ACTIVITY]


def get_episode_comments(episode_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _read_social()
        comments = list((data.get("comments") or {}).get(episode_id) or [])
    comments.sort(key=lambda c: c.get("created_at") or "", reverse=True)
    return comments[:limit]


def add_episode_comment(
    episode_id: str,
    user_id: str,
    content: str,
    *,
    platform: str = "",
) -> Dict[str, Any]:
    text = (content or "").strip()
    if not text:
        return {"success": False, "error": "content required"}
    if len(text) > 2000:
        return {"success": False, "error": "content too long (max 2000)"}

    from backend.services.podcast_service import get_episode
    if not get_episode(episode_id):
        return {"success": False, "error": "episode_not_found"}

    comment = {
        "id": f"pcc-{uuid.uuid4().hex[:10]}",
        "episode_id": episode_id,
        "user_id": user_id,
        "content": text,
        "platform": platform or "podcast",
        "created_at": _iso(),
        "likes": [],
    }

    with _LOCK:
        data = _read_social()
        comments_map = data.setdefault("comments", {})
        ep_comments = list(comments_map.get(episode_id) or [])
        ep_comments.insert(0, comment)
        comments_map[episode_id] = ep_comments[:_MAX_COMMENTS]
        _push_activity(data, {
            "type": "comment",
            "episode_id": episode_id,
            "user_id": user_id,
            "comment_id": comment["id"],
            "preview": text[:120],
            "at": comment["created_at"],
        })
        _write_social(data)

    reward = {}
    try:
        from backend.services.podcast_crypto_rewards_service import award_comment_reward
        reward = award_comment_reward(user_id, episode_id, comment["id"])
    except Exception:
        pass

    return {"success": True, "comment": comment, "crypto_reward": reward}


def like_episode(episode_id: str, user_id: str) -> Dict[str, Any]:
    from backend.services.podcast_service import get_episode
    if not get_episode(episode_id):
        return {"success": False, "error": "episode_not_found"}

    with _LOCK:
        data = _read_social()
        likes_map = data.setdefault("likes", {})
        ep_likes = list(likes_map.get(episode_id) or [])
        if user_id in ep_likes:
            return {"success": True, "liked": True, "like_count": len(ep_likes), "duplicate": True}
        ep_likes.append(user_id)
        likes_map[episode_id] = ep_likes
        _push_activity(data, {
            "type": "like",
            "episode_id": episode_id,
            "user_id": user_id,
            "at": _iso(),
        })
        _write_social(data)

    return {"success": True, "liked": True, "like_count": len(ep_likes)}


def get_episode_like_count(episode_id: str) -> int:
    with _LOCK:
        data = _read_social()
        return len((data.get("likes") or {}).get(episode_id) or [])


def user_liked_episode(episode_id: str, user_id: str) -> bool:
    with _LOCK:
        data = _read_social()
        return user_id in ((data.get("likes") or {}).get(episode_id) or [])


def follow_channel(channel_id: str, user_id: str) -> Dict[str, Any]:
    from backend.services.podcast_service import get_channel
    if not get_channel(channel_id):
        return {"success": False, "error": "channel_not_found"}

    with _LOCK:
        data = _read_social()
        follows_map = data.setdefault("follows", {})
        ch_follows = list(follows_map.get(channel_id) or [])
        if user_id not in ch_follows:
            ch_follows.append(user_id)
            follows_map[channel_id] = ch_follows
            _push_activity(data, {
                "type": "follow",
                "channel_id": channel_id,
                "user_id": user_id,
                "at": _iso(),
            })
            _write_social(data)

    return {"success": True, "channel_id": channel_id, "follower_count": len(ch_follows)}


def get_channel_follower_count(channel_id: str) -> int:
    with _LOCK:
        data = _read_social()
        return len((data.get("follows") or {}).get(channel_id) or [])


def get_activity_feed(limit: int = 30) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _read_social()
        return list(data.get("activity") or [])[:limit]


def get_portal_lines(site_id: Optional[str] = None) -> Dict[str, Any]:
    path = os.path.join(_BASE, "data", "podcast_portal_lines.json")
    raw = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        pass

    sites = list(raw.get("sites") or [])
    site = next((s for s in sites if s.get("id") == site_id), None) if site_id else None

    latest = None
    try:
        from backend.services.podcast_service import get_episodes
        eps = get_episodes()
        if eps:
            latest = {"id": eps[0].get("id"), "title": eps[0].get("title")}
    except Exception:
        pass

    news_headline = None
    try:
        feed = get_news_feed(limit=1)
        if feed:
            news_headline = {"id": feed[0].get("id"), "title": feed[0].get("title")}
    except Exception:
        pass

    return {
        "success": True,
        "site": site,
        "line": (site or {}).get("line") or raw.get("default_line"),
        "comment_hint": (site or {}).get("comment_hint") or raw.get("default_comment_hint"),
        "flavor": raw.get("flavor") or "blue_bubble_cheese_gum",
        "sites": sites,
        "latest_episode": latest,
        "latest_news": news_headline,
        "podcast_url": "/podcast",
        "news_url": "/podcast#news",
    }


def _load_platform_news(limit: int = 30) -> List[Dict[str, Any]]:
    news_path = os.path.join(_BASE, "data", "platform_news.json")
    if not os.path.isfile(news_path):
        return []
    try:
        with open(news_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = list(data.get("items") or [])
        items.sort(key=lambda x: x.get("date") or "", reverse=True)
        return items[:limit]
    except Exception:
        return []


def get_news_comments(news_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    with _LOCK:
        data = _read_social()
        comments = list((data.get("news_comments") or {}).get(news_id) or [])
    comments.sort(key=lambda c: c.get("created_at") or "", reverse=True)
    return comments[:limit]


def add_news_comment(news_id: str, user_id: str, content: str) -> Dict[str, Any]:
    text = (content or "").strip()
    if not text:
        return {"success": False, "error": "content required"}
    if len(text) > 2000:
        return {"success": False, "error": "content too long"}

    comment = {
        "id": f"pnc-{uuid.uuid4().hex[:10]}",
        "news_id": news_id,
        "user_id": user_id,
        "content": text,
        "created_at": _iso(),
    }

    with _LOCK:
        data = _read_social()
        nc = data.setdefault("news_comments", {})
        lst = list(nc.get(news_id) or [])
        lst.insert(0, comment)
        nc[news_id] = lst[:200]
        _push_activity(data, {
            "type": "news_comment",
            "news_id": news_id,
            "user_id": user_id,
            "preview": text[:120],
            "at": comment["created_at"],
        })
        _write_social(data)

    reward = {}
    try:
        from backend.services.podcast_crypto_rewards_service import award_news_comment_reward
        reward = award_news_comment_reward(user_id, news_id, comment["id"])
    except Exception:
        pass

    return {"success": True, "comment": comment, "crypto_reward": reward}


def get_news_feed(limit: int = 20) -> List[Dict[str, Any]]:
    items = _load_platform_news(limit)
    out = []
    for item in items:
        nid = item.get("id") or ""
        out.append({
            **item,
            "comment_count": len(get_news_comments(nid, limit=999)),
            "podcast_discuss_url": f"/podcast#news-{nid}",
        })
    return out
