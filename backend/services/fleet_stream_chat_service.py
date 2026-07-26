"""Public fleet monitor live chat — live, news, events + MN2 reward drops."""
from __future__ import annotations

import json
import os
import random
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LIVE_PATH = os.path.join(_BASE, "data", "fleet_stream_live.json")
_REWARDS_PATH = os.path.join(_BASE, "data", "fleet_stream_rewards.json")
_MSG_DIR = os.path.join(_BASE, "logs", "fleet_stream_chat")
_MSG_FILE = os.path.join(_MSG_DIR, "messages.jsonl")
_CLAIMS_FILE = os.path.join(_MSG_DIR, "claims.json")
_DAILY_FILE = os.path.join(_MSG_DIR, "daily_mn2.json")

_LOCK = threading.RLock()
_MSG_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_MAX_MSG = 420
_MAX_STORE = 800

_CHANNELS = frozenset({"live", "news", "events"})
_VIDEO_ID_RE = re.compile(r"^[\w-]{6,32}$")


def sanitize_youtube_video_id(raw: str) -> str:
    vid = (raw or "").strip()
    return vid if _VIDEO_ID_RE.match(vid) else ""


def build_youtube_embed_url(
    video_id: str,
    cfg: Optional[Dict[str, Any]] = None,
    *,
    mute: Optional[bool] = None,
    site_origin: Optional[str] = None,
) -> str:
    vid = sanitize_youtube_video_id(video_id)
    if not vid:
        return ""
    cfg = cfg or {}
    emb = cfg.get("embed") if isinstance(cfg.get("embed"), dict) else {}
    domain = (cfg.get("youtube_embed_domain") or "https://www.youtube.com").rstrip("/")
    if emb.get("use_nocookie"):
        domain = "https://www.youtube-nocookie.com"
    params: List[str] = []
    if emb.get("autoplay", True):
        params.append("autoplay=1")
    else:
        params.append("autoplay=0")
    muted = emb.get("mute", True) if mute is None else bool(mute)
    params.append("mute=1" if muted else "mute=0")
    if emb.get("modest_branding", True):
        params.append("modestbranding=1")
    if emb.get("rel") is False:
        params.append("rel=0")
    if emb.get("playsinline", True):
        params.append("playsinline=1")
    if emb.get("controls", True):
        params.append("controls=1")
    if emb.get("fs", True):
        params.append("fs=1")
    iv = emb.get("iv_load_policy")
    if iv in (1, 3):
        params.append(f"iv_load_policy={iv}")
    origin = (site_origin or os.environ.get("PUBLIC_SITE_URL") or "").strip().rstrip("/")
    if origin:
        params.append("origin=" + quote(origin, safe=""))
    return f"{domain}/embed/{vid}?" + "&".join(params)


def youtube_public_urls(cfg: Dict[str, Any]) -> Dict[str, str]:
    vid = sanitize_youtube_video_id(cfg.get("youtube_video_id") or "")
    watch = (cfg.get("youtube_watch_url") or "").strip()
    studio = (cfg.get("youtube_studio_url") or "").strip()
    channel = (cfg.get("youtube_channel_url") or "").strip()
    if vid and not watch:
        watch = f"https://www.youtube.com/watch?v={vid}"
    if vid and not studio:
        studio = f"https://studio.youtube.com/video/{vid}/livestreaming"
    return {
        "video_id": vid,
        "watch_url": watch,
        "studio_url": studio,
        "channel_url": channel,
        "embed_url": build_youtube_embed_url(vid, cfg, mute=True),
        "embed_url_unmuted": build_youtube_embed_url(vid, cfg, mute=False),
    }


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def live_config() -> Dict[str, Any]:
    raw = _read_json(_LIVE_PATH, {})
    return raw if isinstance(raw, dict) else {}


def rewards_config() -> Dict[str, Any]:
    raw = _read_json(_REWARDS_PATH, {})
    return raw if isinstance(raw, dict) else {}


def _sanitize_message(text: str) -> str:
    t = _MSG_RE.sub("", (text or "").strip())
    return t[:_MAX_MSG]


def _sanitize_handle(handle: str) -> str:
    h = re.sub(r"[^\w\-. ]", "", (handle or "").strip())[:32]
    return h or "Guest"


def _append_message(row: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(_MSG_DIR, exist_ok=True)
    with _LOCK:
        with open(_MSG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def list_messages(
    *,
    channel: str = "live",
    since_id: Optional[str] = None,
    limit: int = 80,
) -> List[Dict[str, Any]]:
    ch = (channel or "live").lower()
    if ch not in _CHANNELS:
        ch = "live"
    lim = max(1, min(200, int(limit or 80)))
    rows: List[Dict[str, Any]] = []
    if not os.path.isfile(_MSG_FILE):
        return rows
    try:
        with open(_MSG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if (row.get("channel") or "live") != ch:
                    continue
                rows.append(row)
    except Exception:
        return []
    if since_id:
        idx = next((i for i, r in enumerate(rows) if r.get("id") == since_id), -1)
        if idx >= 0:
            rows = rows[idx + 1 :]
    return rows[-lim:]


def _daily_mn2(user_id: str) -> float:
    data = _read_json(_DAILY_FILE, {})
    key = f"{user_id}:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    return float((data.get(key) or {}).get("total") or 0)


def _add_daily_mn2(user_id: str, amount: float) -> None:
    with _LOCK:
        data = _read_json(_DAILY_FILE, {})
        key = f"{user_id}:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        rec = data.get(key) or {"total": 0.0}
        rec["total"] = round(float(rec.get("total") or 0) + amount, 8)
        data[key] = rec
        _write_json(_DAILY_FILE, data)


def _maybe_onchain(user_id: str, amount: float, reference: str, *, prefer: bool = False) -> Dict[str, Any]:
    cfg = (rewards_config().get("onchain") or {})
    if not cfg.get("enabled") and not prefer:
        return {"onchain": False}
    if not cfg.get("enabled"):
        return {"onchain": False}
    amt = float(amount)
    if amt < float(cfg.get("min_mn2") or 0.001):
        return {"onchain": False}
    if amt > float(cfg.get("max_per_event_mn2") or 0.01):
        amt = float(cfg.get("max_per_event_mn2") or 0.01)
    try:
        from backend.services.mn2_wallet_service import get_or_create_deposit_address

        addr_res = get_or_create_deposit_address(user_id)
        addr = (addr_res or {}).get("deposit_address") if isinstance(addr_res, dict) else None
        if not addr:
            return {"onchain": False, "error": "no_address"}
        from backend.services import mn2_rpc_client as rpc

        tx = rpc.sendtoaddress(str(addr), round(amt, 8))
        txid = tx.get("txid") or tx.get("result")
        return {"onchain": True, "txid": txid, "amount": amt, "address": str(addr)[:12] + "…"}
    except Exception as exc:
        return {"onchain": False, "error": str(exc)[:160]}


def _grant_mn2(
    user_id: str,
    amount: float,
    *,
    source: str,
    reference: str,
    prefer_onchain: bool = False,
) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import is_earn_eligible_user
    from backend.services.game_mn2_rewards import credit_mn2

    cfg = rewards_config()
    cap = float(cfg.get("daily_cap_mn2") or 0.5)
    if not is_earn_eligible_user(user_id):
        return {"success": False, "error": "login_required_for_mn2", "code": "auth"}
    if _daily_mn2(user_id) + amount > cap:
        return {"success": False, "error": "daily_cap", "code": "cap"}

    cr = credit_mn2(user_id, amount, source=source, reference=reference, metadata={"channel": "fleet_stream_chat"})
    if not cr.get("success"):
        return cr
    if not cr.get("duplicate"):
        _add_daily_mn2(user_id, amount)
    chain = _maybe_onchain(user_id, amount, reference, prefer=prefer_onchain)
    return {**cr, "chain": chain}


def post_message(
    *,
    channel: str,
    text: str,
    handle: str,
    user_id: Optional[str] = None,
    guest_id: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = live_config()
    if not cfg.get("chat_enabled", True):
        return {"success": False, "error": "chat_disabled"}

    ch = (channel or "live").lower()
    if ch not in _CHANNELS:
        ch = "live"
    body = _sanitize_message(text)
    if len(body) < 1:
        return {"success": False, "error": "empty_message"}
    if len(body) > _MAX_MSG:
        return {"success": False, "error": "too_long"}

    uid = (user_id or "").strip() or (guest_id or "").strip()
    if not uid:
        uid = "guest_" + uuid.uuid4().hex[:10]

    row = {
        "id": uuid.uuid4().hex[:16],
        "channel": ch,
        "at": _iso(),
        "handle": _sanitize_handle(handle),
        "text": body,
        "user_ref": uid[:48],
        "kind": "user",
    }
    _append_message(row)

    reward: Dict[str, Any] = {}
    if ch == "live" and user_id:
        amt = float(rewards_config().get("comment_mn2") or 0.0015)
        reward = _grant_mn2(
            user_id,
            amt,
            source="fleet_stream_chat_comment",
            reference=f"fleet_chat:{row['id']}",
        )
        if reward.get("success"):
            _append_message(
                {
                    "id": uuid.uuid4().hex[:16],
                    "channel": "events",
                    "at": _iso(),
                    "handle": "Fleet rewards",
                    "text": f"{row['handle']} earned +{amt} MN2 for chatting live.",
                    "kind": "reward",
                    "reward_mn2": amt,
                }
            )

    return {"success": True, "message": row, "reward": reward}


def ingest_news_to_chat(limit: int = 5) -> List[Dict[str, Any]]:
    """Push latest platform news headlines into the news channel (idempotent per news id)."""
    from backend.routes.platform_news_routes import _load_news

    posted: List[Dict[str, Any]] = []
    claims = _read_json(_CLAIMS_FILE, {})
    news_claims = claims.setdefault("news_posted", {})
    for item in (_load_news() or [])[: max(1, limit)]:
        nid = str(item.get("id") or "")
        if not nid or news_claims.get(nid):
            continue
        title = (item.get("title") or "News")[:200]
        summary = (item.get("summary") or "")[:280]
        row = {
            "id": uuid.uuid4().hex[:16],
            "channel": "news",
            "at": _iso(),
            "handle": "MN2 News",
            "text": f"{title} — {summary}",
            "kind": "news",
            "news_id": nid,
            "href": item.get("href") or "/news",
        }
        _append_message(row)
        news_claims[nid] = _iso()
        posted.append(row)
    if posted:
        with _LOCK:
            claims = _read_json(_CLAIMS_FILE, {})
            claims.setdefault("news_posted", {}).update(news_claims)
            _write_json(_CLAIMS_FILE, claims)
    return posted


def claim_random_event(user_id: str, *, guest_id: Optional[str] = None) -> Dict[str, Any]:
    cfg = rewards_config()
    if not live_config().get("reward_events_enabled", True):
        return {"success": False, "error": "events_disabled"}

    from backend.services.mn2_earn_auth import is_earn_eligible_user

    if not is_earn_eligible_user(user_id):
        return {"success": False, "error": "login_required_for_mn2", "code": "auth"}

    events = [e for e in (cfg.get("events") or []) if isinstance(e, dict) and e.get("id")]
    if not events:
        return {"success": False, "error": "no_events"}

    with _LOCK:
        claims = _read_json(_CLAIMS_FILE, {})
        user_claims = claims.setdefault("users", {}).setdefault(user_id, {})
        # once-only events
        for ev in events:
            if ev.get("once_per_user") and user_claims.get(ev["id"]):
                continue
        pool = []
        for ev in events:
            if ev.get("once_per_user") and user_claims.get(ev["id"]):
                continue
            w = int(ev.get("weight") or 0)
            if ev.get("once_per_user"):
                pool.append(ev)
            else:
                pool.extend([ev] * max(1, w))
        if not pool:
            return {"success": False, "error": "already_claimed"}
        pick = random.choice(pool)
        eid = str(pick["id"])
        if user_claims.get(eid) and pick.get("once_per_user"):
            return {"success": False, "error": "already_claimed"}
        user_claims[eid] = _iso()
        claims["users"][user_id] = user_claims
        _write_json(_CLAIMS_FILE, claims)

    amt = float(pick.get("mn2") or 0.001)
    ref = f"fleet_evt:{eid}:{user_id}:{int(time.time())}"
    grant = _grant_mn2(
        user_id,
        amt,
        source="fleet_stream_event",
        reference=ref,
        prefer_onchain=bool(pick.get("prefer_onchain")),
    )
    if not grant.get("success"):
        return grant

    title = pick.get("title") or eid
    row = {
        "id": uuid.uuid4().hex[:16],
        "channel": "events",
        "at": _iso(),
        "handle": "Special event",
        "text": f"🎁 {title}: +{amt} MN2 credited"
        + (" · on-chain tx queued" if (grant.get("chain") or {}).get("onchain") else ""),
        "kind": "event",
        "event_id": eid,
        "reward_mn2": amt,
    }
    _append_message(row)
    return {"success": True, "event": pick, "grant": grant, "message": row}


def bootstrap() -> Dict[str, Any]:
    ingest_news_to_chat(limit=6)
    cfg = live_config()
    rc = rewards_config()
    yt = youtube_public_urls(cfg)
    stream_meta = cfg.get("stream") if isinstance(cfg.get("stream"), dict) else {}
    return {
        "success": True,
        "chat_enabled": bool(cfg.get("chat_enabled", True)),
        "poll_ms": int(cfg.get("chat_poll_ms") or 4000),
        "channels": list(_CHANNELS),
        "stream": {
            "title": stream_meta.get("title") or "Fleet live",
            "subtitle": stream_meta.get("subtitle") or "",
            "status_badge": stream_meta.get("status_badge") or "LIVE",
            "chat_placeholder": stream_meta.get("default_chat_placeholder")
            or "Comment on the fleet stream…",
        },
        "youtube": {
            "video_id": yt["video_id"],
            "embed_url": yt["embed_url"],
            "embed_url_unmuted": yt["embed_url_unmuted"],
            "watch_url": yt["watch_url"],
            "studio_url": yt["studio_url"],
            "channel_url": yt["channel_url"],
        },
        "rewards": {
            "event_count": len(rc.get("events") or []),
            "comment_mn2": float(rc.get("comment_mn2") or 0),
            "daily_cap_mn2": float(rc.get("daily_cap_mn2") or 0),
            "onchain_enabled": bool((rc.get("onchain") or {}).get("enabled")),
        },
    }
