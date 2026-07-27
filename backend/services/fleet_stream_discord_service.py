"""Fleet livestream → Discord #general (monitor link + YouTube + GPRS telemetry)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE_URL = (os.environ.get("BASE_URL") or os.environ.get("PUBLIC_SITE_URL") or "").rstrip("/")


def _discord_cfg() -> Dict[str, Any]:
    from backend.services.fleet_stream_chat_service import live_config

    raw = live_config()
    dc = raw.get("discord") if isinstance(raw.get("discord"), dict) else {}
    return {
        "enabled": dc.get("enabled", True),
        "channel": (dc.get("channel") or "general").strip().lower(),
        "prefer_youtube_in_chat": dc.get("prefer_youtube_in_chat", True),
        "monitor_path": dc.get("monitor_path") or "/fleet-progress-monitor/?mode=stream",
        "frontpage_path": dc.get("frontpage_path") or "/",
        "include_gprs_markers": dc.get("include_gprs_markers", True),
        "max_markers_in_post": int(dc.get("max_markers_in_post") or 6),
        "mode": dc.get("mode") or "youtube_and_monitor",
    }


def _abs(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return (_BASE_URL + path) if _BASE_URL else path


def build_discord_live_payload(*, geo: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Discord cannot iframe the full monitor — best UX:
    - Put YouTube watch URL in `content` (native video unfurl in main chat).
    - Rich embed links to the 5D monitor stream layout + GPRS/GPS fields.
    """
    from backend.services.fleet_stream_chat_service import live_config, youtube_public_urls
    from backend.services.fleet_stream_geo_service import public_geo_snapshot

    cfg = _discord_cfg()
    live = live_config()
    yt = youtube_public_urls(live)
    snap = geo if geo is not None else public_geo_snapshot()
    stream_meta = live.get("stream") if isinstance(live.get("stream"), dict) else {}

    monitor_url = _abs(cfg["monitor_path"])
    front_url = _abs(cfg["frontpage_path"])
    title = stream_meta.get("title") or "MasterNoder 5D Fleet Live"
    counts = snap.get("counts") or {}
    center = snap.get("center") or {}

    gprs_lines: List[str] = []
    gps_lines: List[str] = []
    max_m = max(1, min(12, int(cfg.get("max_markers_in_post") or 6)))
    if cfg.get("include_gprs_markers", True):
        for m in snap.get("markers") or []:
            if not isinstance(m, dict):
                continue
            line = (
                f"**{m.get('label') or m.get('id') or 'node'}** "
                f"`{m.get('latitude')}, {m.get('longitude')}`"
            )
            if m.get("mcc_mnc"):
                line += f" · {m['mcc_mnc']}"
            if m.get("kind") == "gprs":
                gprs_lines.append(line)
            elif m.get("kind") == "gps":
                gps_lines.append(line)
            if len(gprs_lines) >= max_m and len(gps_lines) >= max_m:
                break

    fields: List[Dict[str, Any]] = [
        {"name": "GPS fixes", "value": str(counts.get("gps") or 0), "inline": True},
        {"name": "GPRS cells", "value": str(counts.get("gprs") or 0), "inline": True},
        {
            "name": "Map center",
            "value": f"`{center.get('latitude', '—')}, {center.get('longitude', '—')}`",
            "inline": True,
        },
        {
            "name": "5D monitor (OBS / browser)",
            "value": f"[Open stream layout]({monitor_url})",
            "inline": False,
        },
        {
            "name": "Site live rail",
            "value": f"[Frontpage monitor + chat]({front_url})",
            "inline": True,
        },
    ]
    if yt.get("studio_url"):
        fields.append(
            {
                "name": "YouTube Studio",
                "value": f"[Broadcast dashboard]({yt['studio_url']})",
                "inline": True,
            }
        )
    if gprs_lines:
        fields.append(
            {
                "name": "GPRS live",
                "value": "\n".join(gprs_lines[:max_m]),
                "inline": False,
            }
        )
    if gps_lines:
        fields.append(
            {
                "name": "GPS (coarse)",
                "value": "\n".join(gps_lines[:max_m]),
                "inline": False,
            }
        )

    embed = {
        "title": title,
        "url": monitor_url,
        "description": (
            "Watch on **YouTube** in this channel when the link is posted above. "
            "Open the **stream layout** for the full 5D canvas (fleet, themes, voice)."
        ),
        "color": 0x5DFFB0,
        "fields": fields,
        "footer": {
            "text": "GPRS cell relays + browser GPS · assign youtube_stream_agent from stream layout",
        },
    }

    content_parts: List[str] = []
    if cfg.get("prefer_youtube_in_chat") and yt.get("watch_url"):
        content_parts.append(
            f"▶ **Live now** — {title}\n{yt['watch_url']}"
        )
    elif monitor_url:
        content_parts.append(f"▶ **Fleet monitor** — {monitor_url}")

    payload: Dict[str, Any] = {"embeds": [embed]}
    if content_parts:
        payload["content"] = "\n".join(content_parts)
    return payload


def publish_fleet_live_to_discord(
    *,
    message_id: Optional[str] = None,
    channel: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    cfg = _discord_cfg()
    if not cfg.get("enabled", True):
        return {"success": True, "skipped": True, "reason": "discord_disabled"}

    ch = (channel or cfg.get("channel") or "general").strip().lower()
    from backend.services.fleet_stream_geo_service import public_geo_snapshot

    geo = public_geo_snapshot()
    payload = build_discord_live_payload(geo=geo)
    mid = message_id or f"fleet-live:hub:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "channel": ch,
            "message_id": mid,
            "payload": payload,
            "geo_counts": geo.get("counts"),
        }

    from backend.services.discord_service import post_message

    result = post_message(ch, payload, message_id=mid)
    return {
        "success": result.get("success"),
        "channel": ch,
        "message_id": mid,
        "discord": result,
        "geo_counts": geo.get("counts"),
        "mode": cfg.get("mode"),
    }


def publish_gprs_tick_to_discord(*, dry_run: bool = False) -> Dict[str, Any]:
    """Hourly GPRS position tick for main chat (idempotent per hour)."""
    cfg = _discord_cfg()
    if not cfg.get("enabled", True):
        return {"success": True, "skipped": True, "reason": "discord_disabled"}

    from backend.services.fleet_stream_geo_service import public_geo_snapshot

    geo = public_geo_snapshot()
    gprs = [m for m in (geo.get("markers") or []) if m.get("kind") == "gprs"]
    if not gprs:
        return {"success": True, "posted": 0, "reason": "no_gprs"}

    lines = []
    for m in gprs[: int(cfg.get("max_markers_in_post") or 6)]:
        lines.append(
            f"• **{m.get('label', m.get('id'))}** `{m['latitude']}, {m['longitude']}`"
            + (f" ({m['mcc_mnc']})" if m.get("mcc_mnc") else "")
        )
    ch = cfg.get("channel") or "general"
    hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    mid = f"fleet-live:gprs:{hour}"
    monitor_url = _abs(cfg["monitor_path"])
    payload = {
        "embeds": [
            {
                "title": "GPRS relay tick",
                "description": "\n".join(lines),
                "url": monitor_url,
                "color": 0x00D4FF,
                "footer": {"text": f"GPS {geo.get('counts', {}).get('gps', 0)} fixes · fleet monitor"},
            }
        ],
    }
    if dry_run:
        return {"success": True, "dry_run": True, "channel": ch, "message_id": mid, "payload": payload}

    from backend.services.discord_service import post_message

    result = post_message(ch, payload, message_id=mid)
    return {"success": result.get("success"), "channel": ch, "message_id": mid, "discord": result}


def run_fanout(*, dry_run: bool = False) -> Dict[str, Any]:
    """Cron entry — daily hub post + hourly GPRS tick."""
    hub = publish_fleet_live_to_discord(dry_run=dry_run)
    gprs = publish_gprs_tick_to_discord(dry_run=dry_run)
    return {"success": True, "hub": hub, "gprs": gprs}
