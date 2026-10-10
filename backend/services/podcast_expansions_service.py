"""Podcast expansions — RSS, transcripts, chapters, leaderboard."""
from __future__ import annotations

import os
from collections import Counter
from typing import Any, Dict, List
from xml.etree.ElementTree import Element, SubElement, tostring

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SITE = "https://masternoder.dk"


def get_episode_transcript(episode_id: str) -> Dict[str, Any]:
    from backend.services.podcast_service import get_episode
    ep = get_episode(episode_id)
    if not ep:
        return {"success": False, "error": "episode_not_found"}
    transcript = ep.get("transcript")
    if not transcript:
        title = ep.get("title") or episode_id
        desc = ep.get("description") or ""
        transcript = (
            f"[BBCG Intro] Welcome to MasterNoder Podcast — blue bubble cheese gum flavor audio.\n\n"
            f"Episode: {title}\n\n{desc}\n\n"
            f"[Outro] Thanks for listening. Comment on news at masternoder.dk/podcast#news — earn MN2."
        )
    return {
        "success": True,
        "episode_id": episode_id,
        "title": ep.get("title"),
        "transcript": transcript,
        "language": ep.get("language") or "en",
        "auto_generated": not bool(ep.get("transcript")),
    }


def get_episode_chapters(episode_id: str) -> Dict[str, Any]:
    from backend.services.podcast_service import get_episode
    ep = get_episode(episode_id)
    if not ep:
        return {"success": False, "error": "episode_not_found"}
    chapters = list(ep.get("chapters") or [])
    if not chapters:
        dur = int(ep.get("duration_sec") or 300)
        chapters = [
            {"title": "BBCG Intro", "start_sec": 0},
            {"title": ep.get("title") or "Main", "start_sec": min(30, dur // 4)},
            {"title": "News & MN2", "start_sec": min(dur // 2, dur - 60)},
            {"title": "Outro", "start_sec": max(0, dur - 45)},
        ]
    return {
        "success": True,
        "episode_id": episode_id,
        "chapters": chapters,
        "auto_generated": not bool(ep.get("chapters")),
    }


def build_rss_feed() -> str:
    from backend.services.podcast_service import get_episodes, get_channels
    channel_map = {c["id"]: c for c in get_channels()}
    root = Element("rss", version="2.0")
    root.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    channel = SubElement(root, "channel")
    SubElement(channel, "title").text = "MasterNoder Podcast — Blue Bubble Cheese Gum"
    SubElement(channel, "link").text = f"{_SITE}/podcast"
    SubElement(channel, "description").text = (
        "AI video, MN2 crypto, Hunters Game — verified sound, news comments, extended BBCG visuals."
    )
    SubElement(channel, "language").text = "en"
    SubElement(channel, "copyright").text = "MasterNoder.dk"
    SubElement(channel, "itunes:author").text = "MasterNoder"
    SubElement(channel, "itunes:category", text="Technology")

    for ep in get_episodes():
        item = SubElement(channel, "item")
        SubElement(item, "title").text = ep.get("title") or ep.get("id")
        SubElement(item, "description").text = ep.get("description") or ""
        SubElement(item, "guid", isPermaLink="false").text = ep.get("id")
        SubElement(item, "pubDate").text = ep.get("published_at") or ""
        eid = ep.get("id", "")
        SubElement(item, "enclosure", url=f"{_SITE}/api/podcast/episodes/{eid}/audio", type="audio/mpeg")
        ch = channel_map.get(ep.get("channel_id") or "")
        if ch:
            SubElement(item, "itunes:author").text = ch.get("name") or "MasterNoder"
        dur = int(ep.get("duration_sec") or 0)
        if dur:
            SubElement(item, "itunes:duration").text = str(dur)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode")


def get_leaderboard(limit: int = 20) -> Dict[str, Any]:
    from backend.services.podcast_social_service import _read_social
    data = _read_social()
    comment_scores: Counter = Counter()
    like_scores: Counter = Counter()
    news_scores: Counter = Counter()
    follow_scores: Counter = Counter()

    for ep_id, comments in (data.get("comments") or {}).items():
        for c in comments or []:
            uid = c.get("user_id") or ""
            if uid:
                comment_scores[uid] += 1

    for ep_id, likers in (data.get("likes") or {}).items():
        for uid in likers or []:
            if uid:
                like_scores[uid] += 1

    for nid, comments in (data.get("news_comments") or {}).items():
        for c in comments or []:
            uid = c.get("user_id") or ""
            if uid:
                news_scores[uid] += 1

    for ch_id, followers in (data.get("follows") or {}).items():
        for uid in followers or []:
            if uid:
                follow_scores[uid] += 1

    all_users = set(comment_scores) | set(like_scores) | set(news_scores) | set(follow_scores)
    ranked = []
    for uid in all_users:
        score = (
            comment_scores[uid] * 3
            + news_scores[uid] * 4
            + like_scores[uid]
            + follow_scores[uid] * 2
        )
        ranked.append({
            "user_id": uid,
            "score": score,
            "comments": comment_scores[uid],
            "news_comments": news_scores[uid],
            "likes": like_scores[uid],
            "follows": follow_scores[uid],
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)

    return {
        "success": True,
        "leaderboard": ranked[:limit],
        "total_participants": len(ranked),
    }
