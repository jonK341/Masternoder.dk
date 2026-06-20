"""Discord outbound/inbound integration — webhooks, role gating, outbox."""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_OUTBOX = os.path.join(_BASE, "logs", "discord_outbox.jsonl")
_CLICKS = os.path.join(_BASE, "logs", "discord_clicks.jsonl")
_SENT_IDS: set = set()


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _append(path: str, row: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")


def _webhook_for_channel(channel: str) -> Optional[str]:
    key = f"DISCORD_CHANNEL_ID_{channel.upper()}"
    url = os.environ.get("DISCORD_WEBHOOK_URL") or os.environ.get(key)
    return url.strip() if url else None


def post_message(
    channel: str,
    payload: Dict[str, Any],
    *,
    message_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Post embed to Discord via webhook. Idempotent when message_id provided."""
    mid = message_id or payload.get("id") or f"{channel}:{payload.get('title', '')}:{_iso()}"
    if mid in _SENT_IDS:
        return {"success": True, "duplicate": True, "message_id": mid}

    webhook = _webhook_for_channel(channel)
    row = {
        "ts": _iso(),
        "channel": channel,
        "message_id": mid,
        "payload": payload,
        "webhook_configured": bool(webhook),
    }
    ok = False
    err = None
    if webhook:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                ok = 200 <= resp.status < 300
        except urllib.error.HTTPError as exc:
            err = f"HTTP {exc.code}"
            if exc.code == 429:
                err = "rate_limited"
        except Exception as exc:
            err = str(exc)
    else:
        err = "webhook_not_configured"

    row["success"] = ok or not webhook
    row["error"] = err
    _append(_OUTBOX, row)
    if ok or not webhook:
        _SENT_IDS.add(mid)

    try:
        from backend.services.activity_events_service import emit
        emit(
            "discord_post_ok" if ok else "discord_post_failed",
            channel="discord",
            payload={"channel": channel, "message_id": mid, "error": err},
        )
    except Exception:
        pass

    return {"success": ok or not webhook, "message_id": mid, "error": err}


def track_click(user_id: Optional[str], link_id: str, meta: Optional[dict] = None) -> None:
    _append(_CLICKS, {"ts": _iso(), "user_id": user_id, "link_id": link_id, "meta": meta or {}})


def recent_outbox(limit: int = 20) -> List[Dict[str, Any]]:
    if not os.path.isfile(_OUTBOX):
        return []
    rows = []
    with open(_OUTBOX, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return list(reversed(rows[-limit:]))


def outbox_stats(limit: int = 50) -> Dict[str, Any]:
    """Summary for ops/health tiles — recent Discord post success rate."""
    rows = recent_outbox(limit)
    if not rows:
        return {
            "status": "unknown",
            "configured": bool(os.environ.get("DISCORD_WEBHOOK_URL")),
            "total_recent": 0,
            "failures_recent": 0,
            "last_post": None,
        }
    failures = sum(1 for r in rows if r.get("success") is False)
    last = rows[0]
    status = "healthy"
    if failures and failures >= max(3, len(rows) // 2):
        status = "degraded"
    elif not os.environ.get("DISCORD_WEBHOOK_URL"):
        status = "unconfigured"
    return {
        "status": status,
        "configured": bool(os.environ.get("DISCORD_WEBHOOK_URL")),
        "total_recent": len(rows),
        "failures_recent": failures,
        "last_post": {
            "ts": last.get("ts"),
            "channel": last.get("channel"),
            "success": last.get("success"),
            "error": last.get("error"),
        },
    }
