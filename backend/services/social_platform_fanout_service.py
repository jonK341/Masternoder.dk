"""Unified social platform fan-out — Discord, Facebook Page, YouTube community queue."""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "social_platform_fanout_config.json")
_EVENTS = os.path.join(_BASE, "logs", "activity_events.jsonl")
_FB_CURSOR = os.path.join(_BASE, "logs", "facebook_fanout_cursor.json")
_YT_CURSOR = os.path.join(_BASE, "logs", "youtube_fanout_cursor.json")
_FB_OUTBOX = os.path.join(_BASE, "logs", "facebook_fanout_outbox.jsonl")
_YT_QUEUE = os.path.join(_BASE, "logs", "youtube_community_queue.jsonl")
_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_cursor(path: str) -> int:
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(json.load(f).get("line") or 0)
    except Exception:
        return 0


def _save_cursor(path: str, line: int) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _LOCK:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"line": line}, f)
        os.replace(tmp, path)


def _append_log(path: str, row: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")


def _read_new_events(
    channels: Optional[List[str]] = None,
    types: Optional[List[str]] = None,
    *,
    cursor_path: str,
) -> tuple[List[Dict[str, Any]], int]:
    if not os.path.isfile(_EVENTS):
        return [], _load_cursor(cursor_path)
    start = _load_cursor(cursor_path)
    ch_set = set(channels) if channels else None
    type_set = set(types) if types else None
    rows: List[Dict[str, Any]] = []
    line_no = 0
    with open(_EVENTS, "r", encoding="utf-8") as f:
        for line in f:
            line_no += 1
            if line_no <= start:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            ch = row.get("channel") or ""
            et = row.get("type") or ""
            if ch_set is not None and ch not in ch_set:
                continue
            if type_set is not None and et not in type_set:
                continue
            rows.append(row)
    return rows, line_no


def _text_for_event(row: Dict[str, Any]) -> Optional[str]:
    et = row.get("type") or ""
    payload = row.get("payload") or {}
    if et == "casino_jackpot_win" and payload.get("share_ok"):
        return (
            f"🎰 Jackpot! {payload.get('anonymized', 'Player')} won "
            f"{payload.get('amount')} {(payload.get('currency') or '').upper()} — {_BASE_URL}/casino/"
        )
    if et == "casino_big_win" and payload.get("share_ok"):
        return (
            f"🏆 Big win on {payload.get('game', 'casino')}: "
            f"+{payload.get('net')} {(payload.get('currency') or '').upper()} — {_BASE_URL}/casino/"
        )
    if et == "casino_tournament_end":
        return (
            f"🏁 Tournament complete: {payload.get('title', 'Casino')} "
            f"pool {payload.get('pool')} {(payload.get('currency') or '').upper()} — {_BASE_URL}/casino/"
        )
    if et == "p2p_market_fill":
        mn2 = float(payload.get("mn2") or 0)
        cfg = _load_config().get("platforms", {}).get("facebook", {})
        if mn2 < float(cfg.get("min_mn2_highlight") or 5):
            return None
        return f"📈 Market fill: {mn2:.4f} MN2 @ {payload.get('coins')} coins — {_BASE_URL}/explorer?tab=market"
    if et == "platform_news":
        title = payload.get("title") or row.get("text") or "Platform update"
        return f"📢 {title} — {_BASE_URL}"
    if et == "camgirl_unlock":
        perf = payload.get("performer") or payload.get("performer_id") or "performer"
        return f"✨ Camgirls spotlight: {perf} — {_BASE_URL}/camgirls/"
    if et == "partner_spotlight":
        return f"🤝 {payload.get('title', 'Partner spotlight')} — {_BASE_URL}{payload.get('path', '/shop/')}"
    if et == "compendium_complete":
        return f"📚 Compendium milestone — {_BASE_URL}/compendium/?calm=1"
    if et == "game_mn2_reward":
        return f"🎮 Game MN2 reward +{payload.get('amount', payload.get('mn2', 0))} — {_BASE_URL}/game/"
    return None


def _post_facebook_page(message: str, *, link: Optional[str] = None) -> Dict[str, Any]:
    token = (os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()
    page_id = (os.environ.get("FACEBOOK_PAGE_ID") or "").strip()
    if not token or not page_id:
        _append_log(_FB_OUTBOX, {"ts": _iso(), "message": message, "link": link, "posted": False, "reason": "no_token"})
        return {"success": True, "queued": True, "reason": "outbox_only"}
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    body: Dict[str, Any] = {"message": message[:63206], "access_token": token}
    if link:
        body["link"] = link
    data = urllib.parse.urlencode(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        _append_log(_FB_OUTBOX, {"ts": _iso(), "message": message, "posted": True, "id": raw.get("id")})
        return {"success": True, "posted": True, "id": raw.get("id")}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:500]
        _append_log(_FB_OUTBOX, {"ts": _iso(), "message": message, "posted": False, "error": err})
        return {"success": False, "error": err}


def _queue_youtube_community(message: str, *, link: Optional[str] = None) -> Dict[str, Any]:
    """YouTube Community posts require manual publish or YouTube Data API — queue for ops."""
    row = {"ts": _iso(), "message": message, "link": link, "status": "queued"}
    _append_log(_YT_QUEUE, row)
    return {"success": True, "queued": True}


def run_discord_fanouts(*, dry_run: bool = False) -> Dict[str, Any]:
    from backend.services.casino_discord_fanout import run_fanout as casino_run
    from backend.services.game_discord_fanout import run_fanout as game_run
    from backend.services.market_discord_fanout import run_fanout as market_run

    results = {
        "casino": casino_run(dry_run=dry_run),
        "market": market_run(dry_run=dry_run),
        "game": game_run(dry_run=dry_run),
    }
    return {"success": True, "platform": "discord", "channels": results}


def run_facebook_fanout(*, dry_run: bool = False) -> Dict[str, Any]:
    cfg = _load_config()
    fb = cfg.get("platforms", {}).get("facebook", {})
    if not fb.get("enabled", True):
        return {"success": True, "posted": 0, "skipped": True, "reason": "disabled"}
    event_types: List[str] = []
    for group in ("casino", "market", "discovery"):
        event_types.extend(cfg.get("event_types", {}).get(group) or [])
    rows, end_line = _read_new_events(types=event_types, cursor_path=_FB_CURSOR)
    posted = 0
    errors: List[str] = []
    for row in rows:
        text = _text_for_event(row)
        if not text:
            continue
        et = row.get("type") or "event"
        ts = row.get("ts") or ""
        if dry_run:
            posted += 1
            continue
        link = _BASE_URL + "/casino/" if "casino" in et else _BASE_URL
        result = _post_facebook_page(text, link=link)
        if result.get("success"):
            posted += 1
        else:
            errors.append(result.get("error") or "post_failed")
    if not dry_run:
        _save_cursor(_FB_CURSOR, end_line)
    return {"success": True, "platform": "facebook", "processed": len(rows), "posted": posted, "errors": errors}


def run_youtube_fanout(*, dry_run: bool = False) -> Dict[str, Any]:
    cfg = _load_config()
    yt = cfg.get("platforms", {}).get("youtube", {})
    if not yt.get("enabled", True):
        return {"success": True, "queued": 0, "skipped": True, "reason": "disabled"}
    event_types: List[str] = []
    for group in ("casino", "discovery", "game"):
        event_types.extend(cfg.get("event_types", {}).get(group) or [])
    rows, end_line = _read_new_events(types=event_types, cursor_path=_YT_CURSOR)
    queued = 0
    for row in rows:
        text = _text_for_event(row)
        if not text:
            continue
        if dry_run:
            queued += 1
            continue
        _queue_youtube_community(text, link=_BASE_URL)
        queued += 1
    if not dry_run:
        _save_cursor(_YT_CURSOR, end_line)
    return {"success": True, "platform": "youtube", "processed": len(rows), "queued": queued}


def run_discovery_rotator(*, platform: str = "facebook", dry_run: bool = False) -> Dict[str, Any]:
    """Scheduled promo rotator — casino / camgirls / market discovery posts."""
    cfg = _load_config()
    plat = cfg.get("platforms", {}).get(platform, {})
    items = plat.get("discovery_rotator") or []
    if not items:
        return {"success": False, "error": "no_rotator_items"}
    day_idx = datetime.now(timezone.utc).toordinal() % len(items)
    item = items[day_idx]
    path = item.get("path") or "/"
    url = path if str(path).startswith("http") else f"{_BASE_URL}{path}"
    message = f"{item.get('title', 'MasterNoder')} — {item.get('cta', 'Play now')}\n{url}"
    if dry_run:
        return {"success": True, "platform": platform, "dry_run": True, "message": message}
    if platform == "facebook":
        return {**_post_facebook_page(message, link=url), "rotator_id": item.get("id")}
    if platform == "youtube":
        return {**_queue_youtube_community(message, link=url), "rotator_id": item.get("id")}
    from backend.services.discord_service import post_message

    embed = {
        "embeds": [{
            "title": item.get("title", "Discovery"),
            "description": f"{item.get('cta', '')}\n\n[Open]({url})",
            "color": 0x5865F2,
        }],
    }
    result = post_message("announcements", embed, message_id=f"rotator:{platform}:{item.get('id')}:{day_idx}")
    return {"success": result.get("success", False), "platform": platform, "rotator_id": item.get("id"), **result}


def run_all_fanouts(*, dry_run: bool = False) -> Dict[str, Any]:
    return {
        "success": True,
        "ts": _iso(),
        "discord": run_discord_fanouts(dry_run=dry_run),
        "facebook": run_facebook_fanout(dry_run=dry_run),
        "youtube": run_youtube_fanout(dry_run=dry_run),
    }


def get_platform_hub() -> Dict[str, Any]:
    """Feature matrix for UI — implemented vs env-gated."""
    cfg = _load_config()
    fb_token = bool((os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip())
    fb_page = bool((os.environ.get("FACEBOOK_PAGE_ID") or "").strip())
    yt = cfg.get("platforms", {}).get("youtube", {})
    return {
        "success": True,
        "platforms": [
            {
                "id": "discord",
                "label": "Discord",
                "status": "live",
                "features": {
                    "fanout": True,
                    "slash_commands": True,
                    "link_earn_mn2": True,
                    "discovery_rotator": True,
                    "casino_tab": True,
                },
                "links": {
                    "casino_tab": "/casino/?tab=discord",
                    "play_site": "/discord-play/",
                    "interactions": "/api/discord/interactions",
                    "status": "/api/discord/controller/status",
                },
                "rewards": cfg.get("referral_rewards", {}).get("discord_link_mn2", 50),
            },
            {
                "id": "facebook",
                "label": "Facebook / Messenger",
                "status": "live" if fb_token and fb_page else "repo",
                "features": {
                    "fanout": True,
                    "messenger_bot": True,
                    "link_earn_mn2": True,
                    "discovery_rotator": True,
                    "webhook": bool((os.environ.get("FACEBOOK_VERIFY_TOKEN") or "").strip()),
                },
                "links": {
                    "casino_social": "/casino/?tab=social",
                    "webhook": "/api/facebook/casino/webhook",
                    "status": "/api/facebook/casino/status",
                },
                "rewards": cfg.get("referral_rewards", {}).get("facebook_link_mn2", 25),
                "env_needed": [] if fb_token and fb_page else ["FACEBOOK_PAGE_ACCESS_TOKEN", "FACEBOOK_PAGE_ID"],
            },
            {
                "id": "youtube",
                "label": "YouTube",
                "status": "repo",
                "features": {
                    "fanout_queue": True,
                    "discovery_rotator": True,
                    "embed_links": True,
                    "subscribe_mn2": True,
                },
                "links": {
                    "channel": yt.get("channel_url") or "https://www.youtube.com/@masternoder",
                    "podcast": "/podcast/",
                    "casino_clips": "/casino/?tab=social",
                    "status": "/api/youtube/status",
                },
                "rewards": cfg.get("referral_rewards", {}).get("youtube_subscribe_mn2", 0.01),
                "env_needed": ["YOUTUBE_API_KEY (optional)", "YOUTUBE_CHANNEL_ID (optional)"],
            },
        ],
        "cron_endpoints": {
            "all": "/api/social/platforms/fanout/run",
            "rotator_facebook": "/api/social/platforms/rotator/facebook",
            "rotator_youtube": "/api/social/platforms/rotator/youtube",
        },
    }
