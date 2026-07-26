"""Rotating stream chapters with encoded AI copy for fleet monitor / streamer."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CHAPTERS_PATH = os.path.join(_BASE, "data", "fleet_stream_chapters.json")

_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")


def _load_catalog() -> Dict[str, Any]:
    try:
        with open(_CHAPTERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {"chapters": [], "rotate_sec_stream": 75, "rotate_sec_default": 120}


def _scrub(text: str, *, max_len: int = 420) -> str:
    from backend.services.exchange_fleet_progress_monitor_service import _scrub_text

    return _scrub_text(text, max_len=max_len)


def decode_chapter_content(chapter: Dict[str, Any]) -> str:
    raw_b64 = chapter.get("content_b64") or ""
    text = ""
    if raw_b64:
        try:
            text = base64.b64decode(raw_b64).decode("utf-8")
        except Exception:
            text = chapter.get("summary") or ""
    else:
        text = chapter.get("summary") or ""
    return text


def _template_context(fleet_snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    snap = fleet_snapshot or {}
    prog = snap.get("progression") or {}
    fleet = snap.get("fleet") or {}
    trades = snap.get("trades") or {}
    casino = (snap.get("casino") or {}).get("stats") or {}
    agents = (snap.get("agents") or {}).get("stats") or {}
    lanes = snap.get("lanes") or {}
    hot = lanes.get("hot_symbols") or []
    return {
        "commander_level": str(prog.get("commander_level") or 1),
        "fleet_total_xp": str(prog.get("fleet_total_xp") or 0),
        "active_bots": str(fleet.get("active_bots") or 0),
        "bot_count": str(fleet.get("bot_count") or 0),
        "profit_band": str(trades.get("profit_band") or "steady"),
        "hot_symbols": ", ".join(hot[:6]) if hot else "scanning",
        "bets_today": str(casino.get("bets_today") or 0),
        "volume_band": str(casino.get("volume_band") or "steady"),
        "agent_executions": str(agents.get("total_executions") or 0),
        "total_agents": str(agents.get("total_agents") or 0),
        "rewards_unlocked": str(prog.get("rewards_unlocked") or 0),
        "avg_bot_level": str(round(float(prog.get("avg_bot_level") or 1), 1)),
    }


def apply_template(text: str, ctx: Dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        return ctx.get(key, m.group(0))

    return _PLACEHOLDER_RE.sub(repl, text)


def rotation_index(chapter_count: int, *, rotate_sec: int, at_ts: Optional[float] = None) -> int:
    if chapter_count < 1:
        return 0
    ts = at_ts if at_ts is not None else time.time()
    return int(ts // max(30, rotate_sec)) % chapter_count


def chapter_public_view(
    chapter: Dict[str, Any],
    *,
    fleet_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ctx = _template_context(fleet_snapshot)
    decoded = apply_template(decode_chapter_content(chapter), ctx)
    return {
        "id": chapter.get("id"),
        "title": chapter.get("title") or "Chapter",
        "encode_profile": chapter.get("encode_profile") or "broadcast",
        "duration_sec": int(chapter.get("duration_sec") or 75),
        "visual": chapter.get("visual") or "/static/img/fleet/default-bot.svg",
        "ai_content": _scrub_composer(decoded),
        "encoded": True,
    }


def list_chapters_public(
    fleet_snapshot: Optional[Dict[str, Any]] = None,
    *,
    stream_mode: bool = True,
    index: Optional[int] = None,
) -> Dict[str, Any]:
    cat = _load_catalog()
    rows = list(cat.get("chapters") or [])
    rotate = int(
        cat.get("rotate_sec_stream") if stream_mode else cat.get("rotate_sec_default") or 120
    )
    idx = index if index is not None else rotation_index(len(rows), rotate_sec=rotate)
    if rows:
        idx = idx % len(rows)
    current = chapter_public_view(rows[idx], fleet_snapshot=fleet_snapshot) if rows else None
    chapters_out = [chapter_public_view(c, fleet_snapshot=fleet_snapshot) for c in rows]
    return {
        "success": True,
        "rotate_sec": rotate,
        "current_index": idx,
        "chapter_count": len(rows),
        "current": current,
        "chapters": chapters_out,
    }


def composer_for_monitor_payload(payload: Dict[str, Any], *, stream_mode: bool = True) -> Dict[str, Any]:
    return list_chapters_public(payload, stream_mode=stream_mode)
