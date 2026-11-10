"""Live trade ticker for OBS / YouTube / Discord stream overlays.

Appends short trade events from the profit daemon and tracks opt-in interest
for a public trade livestream. Votes are collected for three audiences:
local/ops viewers, YouTube subscribers, and Discord members (no auto-go-live).
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

AUDIENCE_LOCAL = "local"
AUDIENCE_YT_SUB = "youtube_subscriber"
AUDIENCE_DISCORD = "discord"
_AUDIENCES = (AUDIENCE_LOCAL, AUDIENCE_YT_SUB, AUDIENCE_DISCORD)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_audience(audience: str) -> str:
    raw = str(audience or AUDIENCE_LOCAL).strip().lower().replace("-", "_")
    if raw in ("sub", "subscriber", "subscribers", "yt", "youtube", "youtube_sub", "youtube_subscribers"):
        return AUDIENCE_YT_SUB
    if raw in ("discord", "discord_member", "discord_members", "dc", "guild"):
        return AUDIENCE_DISCORD
    if raw in ("ops", "desk", "overlay", "local"):
        return AUDIENCE_LOCAL
    if raw in _AUDIENCES:
        return raw
    return AUDIENCE_LOCAL


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


def _audience_bucket(raw: Dict[str, Any], audience: str) -> Dict[str, Any]:
    audiences = raw.get("audiences") if isinstance(raw.get("audiences"), dict) else {}
    bucket = audiences.get(audience) if isinstance(audiences.get(audience), dict) else {}
    voters = bucket.get("voters") if isinstance(bucket.get("voters"), list) else []
    # Migrate legacy single-list votes into local.
    if audience == AUDIENCE_LOCAL and not voters and isinstance(raw.get("voters"), list):
        voters = list(raw.get("voters") or [])
    return {"voters": [str(v) for v in voters if str(v).strip()]}


def _thresholds() -> Dict[str, int]:
    local_min = int(os.environ.get("PROFIT_YT_STREAM_INTEREST_MIN", "5") or 5)
    sub_min = int(os.environ.get("PROFIT_YT_STREAM_SUB_INTEREST_MIN", str(local_min)) or local_min)
    discord_min = int(os.environ.get("PROFIT_YT_STREAM_DISCORD_INTEREST_MIN", str(local_min)) or local_min)
    return {
        AUDIENCE_LOCAL: local_min,
        AUDIENCE_YT_SUB: sub_min,
        AUDIENCE_DISCORD: discord_min,
    }


def interest_status() -> Dict[str, Any]:
    raw = ex._read_json(_INTEREST_PATH, {}) or {}
    thresholds = _thresholds()
    by_audience: Dict[str, Any] = {}
    total = 0
    for audience in _AUDIENCES:
        bucket = _audience_bucket(raw, audience)
        votes = len(bucket["voters"])
        total += votes
        thr = thresholds[audience]
        by_audience[audience] = {
            "votes": votes,
            "threshold": thr,
            "interested_enough": votes >= thr,
        }
    # Ready when any audience clears its bar.
    interested_enough = any(bool(by_audience[a]["interested_enough"]) for a in _AUDIENCES)
    return {
        "success": True,
        "votes": total,
        "threshold": thresholds[AUDIENCE_LOCAL],
        "interested_enough": interested_enough,
        "audiences": by_audience,
        "local_votes": by_audience[AUDIENCE_LOCAL]["votes"],
        "subscriber_votes": by_audience[AUDIENCE_YT_SUB]["votes"],
        "discord_votes": by_audience[AUDIENCE_DISCORD]["votes"],
        "local_threshold": thresholds[AUDIENCE_LOCAL],
        "subscriber_threshold": thresholds[AUDIENCE_YT_SUB],
        "discord_threshold": thresholds[AUDIENCE_DISCORD],
        "note": (
            "Votes count for local/ops, YouTube subscribers, and Discord members. "
            "Any audience reaching its threshold signals readiness to go live "
            "(fleet-progress-monitor / streamer OBS). No auto go-live."
        ),
        "overlay_path": "/trade-stream",
        "public_vote_path": "/api/youtube/trade-stream-interest",
        "discord_vote_path": "/api/discord/trade-stream-interest",
        "discord_slash": "/streamvote",
        "updated_at": raw.get("updated_at"),
    }


def _is_known_subscriber(user_id: str) -> bool:
    uid = (user_id or "").strip()
    if not uid:
        return False
    try:
        from backend.services.youtube_fanout_service import get_youtube_status

        return bool(get_youtube_status(user_id=uid).get("subscribe_claimed"))
    except Exception:
        return False


def register_interest(
    *,
    voter: str = "",
    audience: str = AUDIENCE_LOCAL,
    user_id: str = "",
    self_attest_subscriber: bool = False,
    discord_id: str = "",
) -> Dict[str, Any]:
    """Register an interest vote for local, YouTube subscriber, or Discord audiences."""
    aud = _normalize_audience(audience)
    key = (voter or user_id or discord_id or "anon").strip().lower()[:64] or "anon"
    uid = (user_id or "").strip()
    did = (discord_id or "").strip()

    subscriber_verified = False
    if aud == AUDIENCE_YT_SUB:
        # Accept: prior subscribe-claim OR explicit self-attest from the YouTube vote CTA.
        subscriber_verified = _is_known_subscriber(uid) or bool(self_attest_subscriber)
        if not subscriber_verified and not self_attest_subscriber:
            # Soft-accept self-attest when audience is explicitly youtube_subscriber
            # (link in YouTube description/chat). Mark as attested.
            subscriber_verified = True
            self_attest_subscriber = True
        key = f"yt:{(uid or key)}"
    elif aud == AUDIENCE_DISCORD:
        key = f"dc:{(did or key)}"

    raw = ex._read_json(_INTEREST_PATH, {}) or {}
    audiences = raw.get("audiences") if isinstance(raw.get("audiences"), dict) else {}
    # One-time migrate legacy list → local bucket.
    if isinstance(raw.get("voters"), list) and AUDIENCE_LOCAL not in audiences:
        audiences[AUDIENCE_LOCAL] = {"voters": list(raw.get("voters") or [])}
    bucket = audiences.get(aud) if isinstance(audiences.get(aud), dict) else {"voters": []}
    voters = [str(v) for v in (bucket.get("voters") or []) if str(v).strip()]
    if key not in voters:
        voters.append(key)
    audiences[aud] = {
        "voters": voters[-500:],
        "updated_at": _iso(),
    }
    raw["audiences"] = audiences
    raw["votes"] = sum(len((audiences.get(a) or {}).get("voters") or []) for a in _AUDIENCES)
    raw["updated_at"] = _iso()
    if aud == AUDIENCE_YT_SUB:
        raw["last_subscriber_vote"] = {
            "voter": key,
            "user_id": uid or None,
            "self_attest": bool(self_attest_subscriber),
            "verified_claim": _is_known_subscriber(uid),
            "ts": _iso(),
        }
    if aud == AUDIENCE_DISCORD:
        raw["last_discord_vote"] = {
            "voter": key,
            "discord_id": did or None,
            "user_id": uid or None,
            "ts": _iso(),
        }
    ex._write_json(_INTEREST_PATH, raw)
    status = interest_status()
    status["registered"] = True
    status["audience"] = aud
    status["subscriber_attested"] = bool(self_attest_subscriber) if aud == AUDIENCE_YT_SUB else False
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
