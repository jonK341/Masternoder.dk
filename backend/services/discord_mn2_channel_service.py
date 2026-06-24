"""Terminal-editable MN2 Discord channel — webhooks, topic, stream fan-out, info digests."""
from __future__ import annotations

import json
import os
import re
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "discord_mn2_channel.json")
_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")

_DEFAULT_STREAMS = {
    "casino": True,
    "game": True,
    "market": True,
    "generator": True,
    "mn2_ledger": True,
    "social": False,
}


def _iso_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_raw() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_raw(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    tmp = _CONFIG_PATH + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _CONFIG_PATH)
    reload_config()


def reload_config() -> Dict[str, Any]:
    with _LOCK:
        _CACHE.clear()
    return get_config()


def get_config() -> Dict[str, Any]:
    with _LOCK:
        if _CACHE.get("config"):
            return dict(_CACHE["config"])
    raw = _load_raw()
    streams = raw.get("enabled_streams") if isinstance(raw.get("enabled_streams"), dict) else {}
    merged_streams = {**_DEFAULT_STREAMS, **{k: bool(v) for k, v in streams.items()}}
    cfg = {
        "version": raw.get("version") or "1.0.0",
        "enabled": bool(raw.get("enabled", True)),
        "channel_id": (raw.get("channel_id") or "").strip(),
        "webhook_url": (raw.get("webhook_url") or "").strip(),
        "env_webhook_key": (raw.get("env_webhook_key") or "DISCORD_CHANNEL_ID_MN2").strip(),
        "topic": (raw.get("topic") or "").strip(),
        "pinned_info": raw.get("pinned_info") if isinstance(raw.get("pinned_info"), dict) else {},
        "info_links": raw.get("info_links") if isinstance(raw.get("info_links"), list) else [],
        "enabled_streams": merged_streams,
        "stream_channel_map": raw.get("stream_channel_map") if isinstance(raw.get("stream_channel_map"), dict) else {},
        "digest": raw.get("digest") if isinstance(raw.get("digest"), dict) else {},
        "compliance_note": raw.get("compliance_note") or "",
        "config_path": _CONFIG_PATH,
    }
    with _LOCK:
        _CACHE["config"] = cfg
    return dict(cfg)


def resolve_webhook() -> Optional[str]:
    cfg = get_config()
    if cfg.get("webhook_url"):
        return cfg["webhook_url"]
    env_key = cfg.get("env_webhook_key") or "DISCORD_CHANNEL_ID_MN2"
    env_val = (os.environ.get(env_key) or "").strip()
    if env_val and env_val.startswith("http"):
        return env_val
    return (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip() or None


_WEBHOOK_URL_RE = re.compile(
    r"^https://(?:discord\.com|discordapp\.com)/api/webhooks/(\d+)/([^/?#]+)",
    re.I,
)


def resolve_channel_id_from_webhook() -> Optional[str]:
    """Resolve Discord channel_id via webhook metadata (no bot token required)."""
    wh = resolve_webhook()
    if not wh:
        return None
    m = _WEBHOOK_URL_RE.match(wh.strip())
    if not m:
        return None
    webhook_id, token = m.group(1), m.group(2)
    url = f"https://discord.com/api/v10/webhooks/{webhook_id}/{token}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MasternoderBot/1.0 (+https://masternoder.dk)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            cid = str(data.get("channel_id") or "").strip()
            return cid or None
    except Exception:
        return None


def ensure_channel_id() -> Dict[str, Any]:
    """Fill channel_id from env or webhook lookup when missing."""
    cfg = get_config()
    existing = (cfg.get("channel_id") or "").strip()
    if existing.isdigit():
        return {"success": True, "channel_id": existing, "source": "config"}

    env_cid = (os.environ.get("DISCORD_CHANNEL_ID_MN2") or "").strip()
    if env_cid.isdigit():
        set_channel_id(env_cid)
        return {"success": True, "channel_id": env_cid, "source": "env"}

    from_webhook = resolve_channel_id_from_webhook()
    if from_webhook:
        set_channel_id(from_webhook)
        return {"success": True, "channel_id": from_webhook, "source": "webhook"}

    return {"success": False, "error": "channel_id_not_resolved"}


def _peek_services_catalog() -> Optional[Dict[str, Any]]:
    """Return cached catalog only — never blocks on live probes."""
    try:
        from backend.services import mn2_services_hub
        import time as _time

        now = _time.time()
        with mn2_services_hub._LOCK:
            ent = mn2_services_hub._CACHE.get("catalog")
            if ent and (now - ent.get("ts", 0)) < mn2_services_hub._CACHE_TTL:
                val = ent.get("value")
                return val if isinstance(val, dict) else None
    except Exception:
        pass
    return None


def _services_catalog(*, timeout_sec: float = 5.0, cache_only: bool = False) -> Dict[str, Any]:
    if cache_only:
        cached = _peek_services_catalog()
        if cached:
            return cached
        return {}

    from backend.services.mn2_services_hub import get_services_catalog

    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(get_services_catalog, use_cache=True)
        try:
            cat = fut.result(timeout=timeout_sec)
        except FuturesTimeout:
            cached = _peek_services_catalog()
            if cached:
                return cached
            raise TimeoutError(f"service catalog probe timed out after {timeout_sec}s")
    return cat if isinstance(cat, dict) else {}


def _stream_for_source_channel(channel: str) -> Optional[str]:
    ch = (channel or "").strip().lower()
    cfg = get_config()
    mapping = cfg.get("stream_channel_map") or {}
    if ch in mapping:
        return str(mapping[ch])
    if ch in _DEFAULT_STREAMS:
        return ch
    return None


def stream_enabled(stream: str) -> bool:
    cfg = get_config()
    if not cfg.get("enabled"):
        return False
    streams = cfg.get("enabled_streams") or {}
    return bool(streams.get(stream))


def should_mirror_channel(channel: str) -> bool:
    stream = _stream_for_source_channel(channel)
    if not stream:
        return False
    return stream_enabled(stream)


def mirror_post(source_channel: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Mirror a webhook payload into #mn2 when the source stream is enabled."""
    if not should_mirror_channel(source_channel):
        return None
    stream = _stream_for_source_channel(source_channel) or source_channel
    embeds = payload.get("embeds")
    if isinstance(embeds, list) and embeds:
        first = dict(embeds[0]) if isinstance(embeds[0], dict) else {}
        title = first.get("title") or "MN2 update"
        first["title"] = f"[{stream}] {title}"[:256]
        first.setdefault("footer", {"text": "Mirrored to MN2 hub · claim on masternoder.dk"})
        mirror_payload = {"embeds": [first]}
    else:
        mirror_payload = {
            "embeds": [{
                "title": f"MN2 stream · {stream}",
                "description": (payload.get("content") or json.dumps(payload))[:2000],
                "footer": {"text": "Mirrored · no custody on Discord"},
            }],
        }
    from backend.services.discord_service import post_message

    mid = f"mn2-mirror:{stream}:{source_channel}:{_iso_day()}:{hash(json.dumps(payload, sort_keys=True, default=str)) % 10_000_000}"
    return post_message("mn2", mirror_payload, message_id=mid)


def build_info_embed(*, cache_only_probe: bool = False) -> Dict[str, Any]:
    """Rich MN2 hub embed — services probe + config links."""
    cfg = get_config()
    lines: List[str] = []
    try:
        cat = _services_catalog(cache_only=cache_only_probe)
        summary = cat.get("summary") or {}
        if summary:
            lines.append(
                f"**Network:** {summary.get('overall', 'unknown')} "
                f"({summary.get('healthy', 0)}/{summary.get('total', 0)} services healthy)"
            )
            for svc in (cat.get("services") or [])[:6]:
                if not isinstance(svc, dict):
                    continue
                st = svc.get("status") or "unknown"
                lines.append(f"• **{svc.get('name')}** — {st}")
        elif cache_only_probe:
            lines.append("**Network:** cached probe unavailable — use `/mn2` for live status")
    except Exception as exc:
        lines.append(f"Service probe unavailable: {exc}")

    lines.append("")
    lines.append("**Quick links**")
    for link in (cfg.get("info_links") or [])[:8]:
        if not isinstance(link, dict):
            continue
        path = link.get("path") or "/"
        url = path if str(path).startswith("http") else f"{_BASE_URL}{path if str(path).startswith('/') else '/' + path}"
        lines.append(f"• [{link.get('label', 'Link')}]({url})")

    lines.append("")
    lines.append("`/mn2` · `/balance` · `/deposit` · `/network` — rewards on-site only.")
    pinned = cfg.get("pinned_info") or {}
    title = pinned.get("title") or "MN2 Hub status"
    return {
        "embeds": [{
            "title": title,
            "description": "\n".join(lines)[:4096],
            "url": f"{_BASE_URL}/explorer/",
            "footer": {"text": cfg.get("compliance_note") or "Gate S — no custody in Discord"},
        }],
    }


def post_info_digest(*, force: bool = False) -> Dict[str, Any]:
    """Post MN2 hub info digest to the MN2 channel."""
    cfg = get_config()
    digest = cfg.get("digest") or {}
    if not cfg.get("enabled"):
        return {"success": False, "error": "mn2_channel_disabled"}
    if not force and not digest.get("enabled", True):
        return {"success": False, "error": "digest_disabled"}
    hour = int(digest.get("hour_utc") or 12)
    now = datetime.now(timezone.utc)
    if not force and now.hour != hour:
        return {"success": True, "skipped": True, "reason": f"hour_mismatch (now {now.hour} UTC, target {hour})"}

    from backend.services.discord_service import post_message

    payload = build_info_embed(cache_only_probe=True)
    prefix = (digest.get("message_id_prefix") or "mn2-digest").strip()
    result = post_message("mn2", payload, message_id=f"{prefix}:{_iso_day()}")
    return {"success": result.get("success"), "discord": result}


def post_pinned_info(*, force: bool = False) -> Dict[str, Any]:
    """Post configured pinned_info body (terminal reload)."""
    cfg = get_config()
    pinned = cfg.get("pinned_info") or {}
    title = (pinned.get("title") or "MasterNoder MN2 Hub").strip()
    body = (pinned.get("body") or "").strip()
    if not body:
        return {"success": False, "error": "pinned_info_empty"}
    payload = {
        "embeds": [{
            "title": title,
            "description": body[:4096],
            "url": f"{_BASE_URL}/explorer/",
            "footer": {"text": cfg.get("compliance_note") or "Gate S — no custody in Discord"},
        }],
    }
    from backend.services.discord_service import post_message

    mid = f"mn2-pinned:{_iso_day()}" if not force else f"mn2-pinned:{_iso_day()}:force"
    result = post_message("mn2", payload, message_id=mid)
    return {"success": result.get("success"), "discord": result}


def test_post() -> Dict[str, Any]:
    payload = {
        "embeds": [{
            "title": "MN2 channel test",
            "description": f"Webhook OK from terminal CLI · {_BASE_URL}",
            "footer": {"text": "Delete this message after verifying delivery"},
        }],
    }
    from backend.services.discord_service import post_message

    result = post_message("mn2", payload, message_id=f"mn2-test:{int(datetime.now(timezone.utc).timestamp())}")
    return {"success": result.get("success"), "webhook_configured": bool(resolve_webhook()), "discord": result}


def set_channel_id(channel_id: str) -> Dict[str, Any]:
    raw = _load_raw()
    raw["channel_id"] = (channel_id or "").strip()
    _save_raw(raw)
    return {"success": True, "channel_id": raw["channel_id"]}


def set_topic(topic: str, *, apply_discord: bool = False) -> Dict[str, Any]:
    raw = _load_raw()
    raw["topic"] = (topic or "").strip()
    _save_raw(raw)
    out: Dict[str, Any] = {"success": True, "topic": raw["topic"]}
    if apply_discord:
        out["discord"] = apply_channel_topic(raw["topic"])
    return out


def set_stream(stream: str, enabled: bool) -> Dict[str, Any]:
    name = (stream or "").strip().lower()
    if name not in _DEFAULT_STREAMS:
        return {"success": False, "error": "unknown_stream", "allowed": list(_DEFAULT_STREAMS)}
    raw = _load_raw()
    streams = raw.get("enabled_streams") if isinstance(raw.get("enabled_streams"), dict) else {}
    streams[name] = bool(enabled)
    raw["enabled_streams"] = streams
    _save_raw(raw)
    return {"success": True, "stream": name, "enabled": bool(enabled)}


def set_webhook_url(url: str) -> Dict[str, Any]:
    raw = _load_raw()
    raw["webhook_url"] = (url or "").strip()
    _save_raw(raw)
    return {"success": True, "webhook_url": raw["webhook_url"] or None}


def apply_channel_topic(topic: Optional[str] = None) -> Dict[str, Any]:
    """PATCH channel topic via Discord Bot API (needs DISCORD_BOT_TOKEN + channel_id)."""
    cfg = get_config()
    channel_id = (cfg.get("channel_id") or "").strip()
    topic_text = (topic if topic is not None else cfg.get("topic") or "").strip()
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    if not channel_id:
        return {"success": False, "error": "channel_id_not_set", "hint": "python scripts/discord_mn2_channel.py set-channel YOUR_CHANNEL_ID"}
    if not token:
        return {"success": False, "error": "DISCORD_BOT_TOKEN missing"}
    if not topic_text:
        return {"success": False, "error": "topic_empty"}
    url = f"https://discord.com/api/v10/channels/{channel_id}"
    body = json.dumps({"topic": topic_text[:1024]}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "MasternoderBot/1.0 (+https://masternoder.dk)",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            return {"success": True, "channel_id": channel_id, "topic": data.get("topic") or topic_text}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:500]
        return {"success": False, "status": exc.code, "error": err or str(exc)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def reload_channel(*, apply_topic: bool = True, post_pinned: bool = True) -> Dict[str, Any]:
    """Reload config cache, sync topic, optionally repost pinned info."""
    cfg = reload_config()
    out: Dict[str, Any] = {"success": True, "config": cfg, "channel_resolve": ensure_channel_id()}
    cfg = get_config()
    out["config"] = cfg
    if apply_topic and cfg.get("topic"):
        out["topic_sync"] = apply_channel_topic(cfg["topic"])
    if post_pinned:
        out["pinned_post"] = post_pinned_info(force=True)
    return out


def format_slash_mn2_reply(*, discord_id: Optional[str] = None) -> str:
    """Text for /mn2 slash command."""
    cfg = get_config()
    lines = ["⛓️ **MN2 Hub**", ""]
    try:
        cat = _services_catalog()
        summary = cat.get("summary") or {}
        lines.append(f"Network: **{summary.get('overall', 'unknown')}** ({summary.get('healthy', 0)}/{summary.get('total', 0)} healthy)")
        for svc in (cat.get("services") or [])[:5]:
            if isinstance(svc, dict):
                lines.append(f"• {svc.get('name')}: {svc.get('status')}")
    except Exception:
        lines.append("Live probe unavailable — check /staking-monitor/")

    lines.append("")
    lines.append("**Earn & trade (on-site)**")
    for link in (cfg.get("info_links") or [])[:6]:
        if not isinstance(link, dict):
            continue
        path = link.get("path") or "/"
        url = f"{_BASE_URL}{path if str(path).startswith('/') else '/' + path}"
        lines.append(f"• {link.get('label')}: {url}")

    did = (discord_id or "").strip()
    if did:
        try:
            from backend.services.discord_controller_service import get_controller_status

            st = get_controller_status(discord_id=did)
            if st.get("linked"):
                from backend.services import casino_service

                bal = casino_service.get_balance(st["user_id"])
                lines.append("")
                lines.append(
                    f"Your balance: **{bal.get('mn2_balance', bal.get('balances', {}).get('mn2', 0))}** MN2 · "
                    f"**{bal.get('coins', 0)}** coins"
                )
            else:
                lines.append("")
                lines.append("Link with `/link CODE` to see your MN2 balance here.")
        except Exception:
            pass

    lines.append("")
    lines.append("Promos: **HOSTMN5** (hosting) · **MARKET-BONUS** · **DISCORD-STARTER** — Shop only.")
    return "\n".join(lines)[:2000]
