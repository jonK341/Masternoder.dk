"""Live trade ticker for OBS / YouTube stream overlays.

Appends short trade events from the profit daemon and tracks opt-in interest
for a public YouTube trade stream (no auto-go-live — interest only).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_EVENTS_PATH = os.path.join(ex._DATA_DIR, "profit_trade_stream.jsonl")
_INTEREST_PATH = os.path.join(ex._DATA_DIR, "profit_youtube_stream_interest.json")
_YT_BROADCAST = os.path.join(ex._BASE, "logs", "profit_youtube_broadcast.jsonl")
_MAX_EVENTS = 400


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append_trade(
    *,
    strategy: str,
    message: str,
    mode: str = "live",
    delta_usd: float = 0.0,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record one trade/stream line for the OBS ticker + YouTube broadcast log."""
    row: Dict[str, Any] = {
        "ts": _iso(),
        "strategy": str(strategy or "profit")[:48],
        "message": str(message or "")[:240],
        "mode": str(mode or "live")[:16],
        "delta_usd": round(float(delta_usd or 0), 4),
    }
    if extra:
        row["extra"] = {str(k)[:32]: str(v)[:80] for k, v in list(extra.items())[:8]}
    os.makedirs(os.path.dirname(_EVENTS_PATH), exist_ok=True)
    with open(_EVENTS_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    try:
        os.makedirs(os.path.dirname(_YT_BROADCAST), exist_ok=True)
        with open(_YT_BROADCAST, "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {"ts": row["ts"], "message": row["message"], "delta_usd": row["delta_usd"]},
                    default=str,
                )
                + "\n"
            )
    except Exception:
        pass
    return {"success": True, "event": row}


def recent_trades(*, limit: int = 40) -> List[Dict[str, Any]]:
    if not os.path.isfile(_EVENTS_PATH):
        return []
    try:
        lines = open(_EVENTS_PATH, encoding="utf-8").read().splitlines()
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for line in lines[-max(1, min(limit, _MAX_EVENTS)):]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def interest_status() -> Dict[str, Any]:
    raw = ex._read_json(_INTEREST_PATH, {}) or {}
    votes = int(raw.get("votes") or 0)
    threshold = int(os.environ.get("PROFIT_YT_STREAM_INTEREST_MIN", "5") or 5)
    return {
        "success": True,
        "votes": votes,
        "threshold": threshold,
        "interested_enough": votes >= threshold,
        "note": (
            "YouTube trade stream stays opt-in. When votes reach the threshold, "
            "ops can go live via fleet-progress-monitor / streamer OBS overlay."
        ),
        "overlay_path": "/trade-stream",
        "updated_at": raw.get("updated_at"),
    }


def register_interest(*, voter: str = "") -> Dict[str, Any]:
    raw = ex._read_json(_INTEREST_PATH, {}) or {}
    voters = raw.get("voters") if isinstance(raw.get("voters"), list) else []
    key = (voter or "anon").strip().lower()[:64] or "anon"
    if key not in voters:
        voters.append(key)
    raw["voters"] = voters[-500:]
    raw["votes"] = len(raw["voters"])
    raw["updated_at"] = _iso()
    ex._write_json(_INTEREST_PATH, raw)
    status = interest_status()
    status["registered"] = True
    return status


def snapshot(*, limit: int = 30) -> Dict[str, Any]:
    trades = recent_trades(limit=limit)
    interest = interest_status()
    return {
        "success": True,
        "trades": trades,
        "interest": interest,
        "live_hint": interest.get("interested_enough"),
    }
