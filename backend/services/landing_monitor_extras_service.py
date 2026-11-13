"""Landing monitor extras — YouTube search, Discord votes, matrix rails, battlefield 3500."""
from __future__ import annotations

import json
import os
import random
import threading
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_VOTES_PATH = os.path.join(_BASE, "data", "landing_monitor_votes.json")

YT_FALLBACK_QUERIES = (
    "MasterNoder2 crypto",
    "bitcoin satoshi network",
    "AI video generator",
    "daemon trading desk",
    "year 3500 battlefield sci-fi",
    "matrix digital rain",
    "discord crypto community",
)

# Curated public videos used when YouTube API key is missing.
YT_FALLBACK_VIDEOS = (
    {"id": "bBcY6jAQJL0", "title": "Bitcoin — digital cash talk", "channel": "Fallback"},
    {"id": "gXMfhme4eew", "title": "Crypto markets overview", "channel": "Fallback"},
    {"id": "KQ6zr6kCPj8", "title": "Party rock anthem (energy cut)", "channel": "Fallback"},
    {"id": "fJ9rUzIMcZQ", "title": "Bohemian Rhapsody — stage energy", "channel": "Fallback"},
    {"id": "9bZkp7q19f0", "title": "Gangnam Style — viral clip", "channel": "Fallback"},
    {"id": "kXYi5s7Hz8s", "title": "Numb — arena pulse", "channel": "Fallback"},
    {"id": "hTWKbfoikeg", "title": "Smells Like Teen Spirit — blast", "channel": "Fallback"},
    {"id": "YQHsXMglC9A", "title": "Hello — vocal stage", "channel": "Fallback"},
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_votes() -> Dict[str, Any]:
    if not os.path.isfile(_VOTES_PATH):
        return {"updated_at": None, "polls": []}
    try:
        with open(_VOTES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"polls": []}
    except Exception:
        return {"polls": []}


def _write_votes(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_VOTES_PATH), exist_ok=True)
    tmp = _VOTES_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, _VOTES_PATH)


def youtube_search(query: str = "", *, limit: int = 6, randomize: bool = True) -> Dict[str, Any]:
    q = (query or "").strip() or random.choice(YT_FALLBACK_QUERIES)
    limit = max(1, min(12, int(limit or 6)))
    videos: List[Dict[str, Any]] = []
    source = "fallback"

    try:
        import importlib.util

        path = os.path.join(
            _BASE,
            "vidgenerator",
            "src",
            "services",
            "data_gathering",
            "api_wrappers.py",
        )
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("mn_yt_wrappers", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                wrapper = mod.YouTubeWrapper()
                raw = wrapper.search_videos(q, max_results=limit) or []
                for row in raw:
                    if not row.get("id"):
                        continue
                    videos.append(
                        {
                            "id": row["id"],
                            "title": row.get("title") or "YouTube video",
                            "channel": row.get("channel") or "",
                            "thumbnail": row.get("thumbnail")
                            or f"https://i.ytimg.com/vi/{row['id']}/hqdefault.jpg",
                            "url": f"https://www.youtube.com/watch?v={row['id']}",
                            "embed_url": f"https://www.youtube.com/embed/{row['id']}",
                        }
                    )
                if videos:
                    source = "youtube_api"
    except Exception:
        videos = []

    if not videos:
        pool = list(YT_FALLBACK_VIDEOS)
        if randomize:
            random.shuffle(pool)
        for row in pool[:limit]:
            videos.append(
                {
                    "id": row["id"],
                    "title": f"{row['title']} · {q}",
                    "channel": row.get("channel") or "MasterNoder",
                    "thumbnail": f"https://i.ytimg.com/vi/{row['id']}/hqdefault.jpg",
                    "url": f"https://www.youtube.com/watch?v={row['id']}",
                    "embed_url": f"https://www.youtube.com/embed/{row['id']}",
                    "search_url": "https://www.youtube.com/results?search_query="
                    + urllib.parse.quote(q),
                }
            )
        source = "fallback_curated"

    pick = random.choice(videos) if videos and randomize else (videos[0] if videos else None)
    return {
        "success": True,
        "query": q,
        "source": source,
        "count": len(videos),
        "videos": videos,
        "random": pick,
        "search_url": "https://www.youtube.com/results?search_query=" + urllib.parse.quote(q),
        "updated_at": _iso(),
    }


def facebook_share_payload(*, url: str = "", quote: str = "") -> Dict[str, Any]:
    # Prefer caller URL; fall back to relative site root (no hardcoded host).
    target = (url or "/").strip() or "/"
    share = "https://www.facebook.com/sharer/sharer.php?u=" + urllib.parse.quote(target, safe="")
    if quote:
        share += "&quote=" + urllib.parse.quote(quote[:200], safe="")
    return {
        "success": True,
        "network": "facebook",
        "url": target,
        "share_url": share,
        "updated_at": _iso(),
    }


def ensure_discord_poll(*, question: Optional[str] = None) -> Dict[str, Any]:
    """Create or return active Discord-style vote for the lobby pipeline."""
    with _LOCK:
        doc = _read_votes()
        polls = doc.get("polls") if isinstance(doc.get("polls"), list) else []
        active = next((p for p in polls if p.get("status") == "open"), None)
        if active:
            return {"success": True, "poll": active, "created": False}

        q = question or "Which lobby stage should lead the next Jon Film cut?"
        options = [
            {"id": "opt_battlefield", "label": "War battlefield 3500", "votes": 0},
            {"id": "opt_matrix", "label": "MN2 matrix rails", "votes": 0},
            {"id": "opt_camgirl", "label": "Camgirl agent stage", "votes": 0},
            {"id": "opt_daemon", "label": "Daemon desk live", "votes": 0},
        ]
        poll = {
            "id": f"poll_{uuid.uuid4().hex[:10]}",
            "question": q,
            "options": options,
            "status": "open",
            "channel": "landing",
            "created_at": _iso(),
            "discord_posted": False,
        }
        # Soft Discord announce (webhook / outbox) — never hard-fail or hang lobby.
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

            from backend.services import discord_service

            def _post():
                return discord_service.post_message(
                    "landing",
                    {
                        "content": f"Lobby vote: {q}\n"
                        + "\n".join(f"{i+1}) {o['label']}" for i, o in enumerate(options)),
                    },
                )

            with ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(_post)
                res = fut.result(timeout=1.2)
            poll["discord_posted"] = bool(res.get("success") if isinstance(res, dict) else res)
        except Exception:
            poll["discord_posted"] = False

        polls.insert(0, poll)
        doc = {"updated_at": _iso(), "polls": polls[:40]}
        _write_votes(doc)
        return {"success": True, "poll": poll, "created": True}


def cast_discord_vote(option_id: str, *, poll_id: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        doc = _read_votes()
        polls = doc.get("polls") if isinstance(doc.get("polls"), list) else []
        poll = None
        if poll_id:
            poll = next((p for p in polls if p.get("id") == poll_id), None)
        if not poll:
            poll = next((p for p in polls if p.get("status") == "open"), None)
        if not poll:
            return {"success": False, "error": "no_open_poll"}
        hit = False
        for opt in poll.get("options") or []:
            if opt.get("id") == option_id:
                opt["votes"] = int(opt.get("votes") or 0) + 1
                hit = True
                break
        if not hit:
            return {"success": False, "error": "bad_option"}
        poll["updated_at"] = _iso()
        doc["updated_at"] = _iso()
        _write_votes(doc)
        return {"success": True, "poll": poll}


def list_votes() -> Dict[str, Any]:
    doc = _read_votes()
    polls = doc.get("polls") if isinstance(doc.get("polls"), list) else []
    open_poll = next((p for p in polls if p.get("status") == "open"), None)
    return {
        "success": True,
        "open": open_poll,
        "polls": polls[:10],
        "updated_at": doc.get("updated_at"),
    }


def matrix_network_lines(*, limit: int = 40) -> Dict[str, Any]:
    """Build matrix-style falling strings from MN2 network stats."""
    lines: List[str] = []
    overview: Dict[str, Any] = {}
    try:
        from backend.services import mn2_chainz

        overview = mn2_chainz.network_overview() or {}
    except Exception:
        overview = {}

    height = overview.get("blocks") or overview.get("height") or overview.get("block_height")
    peers = overview.get("connections") or overview.get("peers")
    diff = overview.get("difficulty")
    hashrate = overview.get("networkhashps") or overview.get("hashrate")
    supply = overview.get("moneysupply") or overview.get("supply")

    def add(label: str, value: Any) -> None:
        if value is None or value == "":
            return
        lines.append(f"MN2::{label}::{value}")

    add("HEIGHT", height)
    add("PEERS", peers)
    add("DIFF", diff)
    add("HASH", hashrate)
    add("SUPPLY", supply)
    add("YEAR", 3500)
    add("THEME", "BATTLEFIELD")
    add("COMM", "UPLINK-ALPHA")

    try:
        from backend.services import mn2_network_stats

        hist = mn2_network_stats.get_history(hours=6.0, limit=12) or []
        for row in hist[-8:]:
            if not isinstance(row, dict):
                continue
            h = row.get("height") or row.get("blocks")
            if h is not None:
                lines.append(f"SNAP::H{h}::{str(row.get('ts') or '')[-8:]}")
    except Exception:
        pass

    # Pad so both rails stay dense.
    while len(lines) < max(12, limit // 2):
        lines.append(f"PACKET::{random.randint(1000, 9999)}::OK")
        lines.append(f"SATS::{random.randint(10, 99)}M::FLOW")

    left = lines[::2][:limit]
    right = lines[1::2][:limit]
    return {
        "success": True,
        "theme": "matrix_mn2",
        "overview": {
            "height": height,
            "peers": peers,
            "difficulty": diff,
            "hashrate": hashrate,
            "supply": supply,
        },
        "left": left,
        "right": right,
        "updated_at": _iso(),
    }


def battlefield_theme() -> Dict[str, Any]:
    return {
        "success": True,
        "id": "war_battlefield_3500",
        "year": 3500,
        "title": "War Battlefield · Year 3500",
        "tagline": "Jon Film combat stage — communication lines stay hot.",
        "comm_lines": [
            {"id": "comm_alpha", "label": "ALPHA RELAY", "status": "online", "freq": "3.5 GHz"},
            {"id": "comm_bravo", "label": "BRAVO MESH", "status": "online", "freq": "7.1 GHz"},
            {"id": "comm_ghost", "label": "GHOST NET", "status": "encrypted", "freq": "14.0 GHz"},
            {"id": "comm_orbit", "label": "ORBIT UPLINK", "status": "online", "freq": "28.2 GHz"},
        ],
        "css_class": "is-battlefield-3500",
        "updated_at": _iso(),
    }
