"""Profit-daemon levels. Twenty assignments define one level.

A level is earned only when the owner sets a vision, a next profit move, and
a non-empty text on every assignment slot. The daemon reads the highest
earned level as its current vision and next profit move, and records whether
the YouTube broadcast is live.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex

ASSIGNMENTS_PER_LEVEL = 20
_TEXT_MAX = 280
_HEADLINE_MAX = 400
_YOUTUBE_MIN_INTERVAL_SEC = 300
_DEFAULT_VIDEO_ID = "-iSYSBSn_8E"
_DEFAULT_CHANNEL_URL = "https://www.youtube.com/@Jon_Ulrik"
_USER_AGENT = "MasterNoderProfitDaemon/1.0"

# Slot order is the level definition. Vision and the next profit move are
# headlines the owner sets; these twenty assignments are what that level means.
ASSIGNMENT_SLOTS: Tuple[Tuple[str, str], ...] = (
    ("vision_who", "Who this level is for"),
    ("vision_outcome", "Outcome this level makes true"),
    ("vision_proof", "Proof the vision landed"),
    ("market", "Market in play"),
    ("venue", "Venue for the move"),
    ("symbol", "Symbol for the move"),
    ("side", "Buy or sell"),
    ("size_cap", "Size cap"),
    ("entry_rule", "Entry rule"),
    ("exit_rule", "Exit rule"),
    ("fee_floor", "Fee floor the move must clear"),
    ("loss_cap", "Loss cap"),
    ("funding", "Funding the move needs"),
    ("inventory_rule", "Inventory rule"),
    ("hedge_or_skip", "Hedge or skip condition"),
    ("sweep_rule", "Where the profit goes"),
    ("stream_check", "What to confirm on the YouTube live stream"),
    ("stream_show", "What the live stream should show"),
    ("news_line", "Line to publish when the move hits"),
    ("commit", "Commit line for this level"),
)

class LevelInputError(ValueError):
    """Rejected level board. ``code`` is a stable API error string."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _iso(ts: Optional[float] = None) -> str:
    moment = datetime.fromtimestamp(ts if ts is not None else time.time(), timezone.utc)
    return moment.isoformat().replace("+00:00", "Z")


def _state_path() -> str:
    return os.path.join(ex._DATA_DIR, "profit_daemon_level.json")


def _clip(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def blank_assignments() -> List[Dict[str, Any]]:
    return [
        {"slot": index, "key": key, "label": label, "text": ""}
        for index, (key, label) in enumerate(ASSIGNMENT_SLOTS, start=1)
    ]


def _empty_state() -> Dict[str, Any]:
    return {"version": 1, "levels": [], "youtube": {}}


def _load() -> Dict[str, Any]:
    raw = ex._read_json(_state_path(), None)
    if not isinstance(raw, dict):
        return _empty_state()
    levels = raw.get("levels")
    youtube = raw.get("youtube")
    return {
        "version": 1,
        "levels": [row for row in levels if isinstance(row, dict)] if isinstance(levels, list) else [],
        "youtube": youtube if isinstance(youtube, dict) else {},
    }


def _save(state: Dict[str, Any]) -> None:
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def _filled_count(assignments: List[Dict[str, Any]]) -> int:
    return sum(1 for row in assignments if str(row.get("text") or "").strip())


def _earned_levels(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [row for row in state.get("levels") or [] if row.get("earned")]


def _working_level(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    levels = state.get("levels") or []
    if levels and not levels[-1].get("earned"):
        return levels[-1]
    return None


def active_directive(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Highest earned level: the vision and next profit move the daemon follows."""
    state = state if state is not None else _load()
    earned = _earned_levels(state)
    if not earned:
        return {
            "level": 0,
            "defined": False,
            "vision": "",
            "next_profit_move": "",
            "assignments": blank_assignments(),
        }
    top = earned[-1]
    return {
        "level": int(top.get("level") or 0),
        "defined": True,
        "vision": str(top.get("vision") or ""),
        "next_profit_move": str(top.get("next_profit_move") or ""),
        "assignments": top.get("assignments") or blank_assignments(),
        "earned_at": top.get("earned_at"),
    }


def _normalize_assignments(raw: Any) -> List[Dict[str, Any]]:
    if raw is None:
        return blank_assignments()
    if not isinstance(raw, list) or len(raw) != ASSIGNMENTS_PER_LEVEL:
        raise LevelInputError("assignments_must_be_20")
    by_slot: Dict[int, str] = {}
    for row in raw:
        if not isinstance(row, dict):
            raise LevelInputError("assignments_must_be_20")
        try:
            slot = int(row.get("slot"))
        except (TypeError, ValueError):
            raise LevelInputError("assignments_must_be_20")
        if slot < 1 or slot > ASSIGNMENTS_PER_LEVEL or slot in by_slot:
            raise LevelInputError("assignments_must_be_20")
        by_slot[slot] = _clip(row.get("text"), _TEXT_MAX)
    if len(by_slot) != ASSIGNMENTS_PER_LEVEL:
        raise LevelInputError("assignments_must_be_20")
    board = blank_assignments()
    for row in board:
        row["text"] = by_slot[row["slot"]]
    return board


def _missing(vision: str, move: str, assignments: List[Dict[str, Any]]) -> List[str]:
    missing: List[str] = []
    if not vision:
        missing.append("vision")
    if not move:
        missing.append("next_profit_move")
    for row in assignments:
        if not str(row.get("text") or "").strip():
            missing.append(str(row.get("key") or row.get("slot")))
    return missing


def assign_level(
    vision: Any,
    next_profit_move: Any,
    assignments: Any = None,
    *,
    level: Optional[int] = None,
) -> Dict[str, Any]:
    """Save a 20-assignment board. A complete board earns that level."""
    vision_text = _clip(vision, _HEADLINE_MAX)
    move_text = _clip(next_profit_move, _HEADLINE_MAX)
    board = _normalize_assignments(assignments)
    state = _load()
    levels: List[Dict[str, Any]] = list(state.get("levels") or [])
    now = _iso()
    missing = _missing(vision_text, move_text, board)
    earned = not missing

    if level is None:
        working = _working_level(state)
        if working is not None:
            target_number = int(working.get("level") or 1)
        else:
            target_number = len(_earned_levels(state)) + 1
    else:
        target_number = int(level)
        if target_number < 1:
            raise LevelInputError("level_out_of_range")
        known = {int(row.get("level") or 0) for row in levels}
        working = _working_level(state)
        next_number = int(working["level"]) if working else len(_earned_levels(state)) + 1
        if target_number not in known and target_number != next_number:
            raise LevelInputError("level_out_of_range")

    record = {
        "level": target_number,
        "earned": earned,
        "vision": vision_text,
        "next_profit_move": move_text,
        "assignments": board,
        "filled": ASSIGNMENTS_PER_LEVEL - len([key for key in missing if key not in ("vision", "next_profit_move")]),
        "missing": missing,
        "updated_at": now,
    }
    if earned:
        record["earned_at"] = now

    replaced = False
    new_levels: List[Dict[str, Any]] = []
    for row in levels:
        number = int(row.get("level") or 0)
        if number == target_number:
            if row.get("earned") and row.get("earned_at") and earned:
                record["earned_at"] = row.get("earned_at")
            new_levels.append(record)
            replaced = True
        elif number < target_number or earned:
            new_levels.append(row)
    if not replaced:
        new_levels.append(record)
    if not earned:
        new_levels = [row for row in new_levels if int(row.get("level") or 0) <= target_number]
    state["levels"] = new_levels
    _save(state)
    out = snapshot(state)
    out.update({
        "success": True,
        "saved_level": target_number,
        "earned": earned,
        "missing": missing,
        "filled": record["filled"],
        "required": ASSIGNMENTS_PER_LEVEL,
    })
    return out


def snapshot(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    state = state if state is not None else _load()
    directive = active_directive(state)
    working = _working_level(state)
    if working is not None:
        board = working
        editing_level = int(working.get("level") or 1)
    else:
        editing_level = int(directive.get("level") or 0) + 1
        board = {
            "level": editing_level,
            "earned": False,
            "vision": "",
            "next_profit_move": "",
            "assignments": blank_assignments(),
            "filled": 0,
            "missing": ["vision", "next_profit_move"] + [key for key, _label in ASSIGNMENT_SLOTS],
        }
    filled = int(board.get("filled") if board.get("filled") is not None else _filled_count(board.get("assignments") or []))
    history = []
    for row in state.get("levels") or []:
        history.append({
            "level": int(row.get("level") or 0),
            "earned": bool(row.get("earned")),
            "vision": str(row.get("vision") or ""),
            "next_profit_move": str(row.get("next_profit_move") or ""),
            "filled": int(row.get("filled") if row.get("filled") is not None else _filled_count(row.get("assignments") or [])),
            "earned_at": row.get("earned_at"),
        })
    return {
        "success": True,
        "assignments_per_level": ASSIGNMENTS_PER_LEVEL,
        "level": int(directive.get("level") or 0),
        "defined": bool(directive.get("defined")),
        "vision": directive.get("vision") or "",
        "next_profit_move": directive.get("next_profit_move") or "",
        "editing_level": editing_level,
        "progress": {
            "filled": filled,
            "required": ASSIGNMENTS_PER_LEVEL,
            "remaining": ASSIGNMENTS_PER_LEVEL - filled,
        },
        "board": {
            "level": editing_level,
            "earned": bool(board.get("earned")),
            "vision": str(board.get("vision") or ""),
            "next_profit_move": str(board.get("next_profit_move") or ""),
            "assignments": board.get("assignments") or blank_assignments(),
            "missing": board.get("missing") or [],
        },
        "slots": [
            {"slot": index, "key": key, "label": label}
            for index, (key, label) in enumerate(ASSIGNMENT_SLOTS, start=1)
        ],
        "levels": history,
        "youtube": state.get("youtube") or {},
    }


def _fetch_text(url: str, timeout: float = 8.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_youtube_live_html(html: str) -> Dict[str, Any]:
    """Read a channel /live or watch HTML page. No network."""
    text = html or ""
    live = (
        "BADGE_STYLE_TYPE_LIVE_NOW" in text
        or bool(re.search(r'"isLiveNow"\s*:\s*true', text))
    )
    title_match = re.search(r'"title"\s*:\s*\{\s*"content"\s*:\s*"([^"\\]+)"', text)
    if not title_match:
        title_match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
    title = ""
    if title_match:
        title = title_match.group(1).replace("\\u0026", "&").strip()
        if title.endswith(" - YouTube"):
            title = title[: -len(" - YouTube")].strip()
    streamed = re.search(r"Streamed ([^\"\\<]{1,40})", text)
    note = "Live now." if live else "Not live."
    if not live and streamed:
        note = "Not live. Last broadcast streamed " + streamed.group(1).strip() + "."
    return {"live": live, "title": title, "note": note}


def parse_youtube_oembed(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return {
        "title": str(payload.get("title") or ""),
        "author": str(payload.get("author_name") or ""),
        "author_url": str(payload.get("author_url") or ""),
    }


def resolve_youtube_target() -> Dict[str, str]:
    video_id = (os.environ.get("YOUTUBE_VIDEO_ID") or "").strip()
    channel = (os.environ.get("YOUTUBE_CHANNEL_URL") or "").strip()
    cfg_path = os.path.join(ex._BASE, "data", "fleet_stream_live.json")
    cfg = ex._read_json(cfg_path, {})
    if isinstance(cfg, dict):
        video_id = video_id or str(cfg.get("youtube_video_id") or "").strip()
        channel = channel or str(cfg.get("youtube_channel_url") or "").strip()
    video_id = video_id or _DEFAULT_VIDEO_ID
    channel = channel or _DEFAULT_CHANNEL_URL
    return {
        "video_id": video_id,
        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
        "channel_url": channel.rstrip("/"),
        "live_url": channel.rstrip("/") + "/live",
        "oembed_url": "https://www.youtube.com/oembed?format=json&url="
        + urllib.parse.quote(f"https://www.youtube.com/watch?v={video_id}", safe=""),
    }


def check_youtube_live(
    *,
    fetch: Optional[Callable[[str], str]] = None,
    persist: bool = True,
) -> Dict[str, Any]:
    """Look up the configured broadcast and record whether it is live."""
    target = resolve_youtube_target()
    getter = fetch or _fetch_text
    result: Dict[str, Any] = {
        "success": True,
        "live": False,
        "video_id": target["video_id"],
        "watch_url": target["watch_url"],
        "channel_url": target["channel_url"],
        "title": "",
        "author": "",
        "note": "Not live.",
        "checked_at": _iso(),
        "ts": time.time(),
    }
    errors: List[str] = []
    try:
        oembed_raw = getter(target["oembed_url"])
        meta = parse_youtube_oembed(json.loads(oembed_raw))
        result["title"] = meta.get("title") or ""
        result["author"] = meta.get("author") or ""
        if meta.get("author_url"):
            result["author_url"] = meta["author_url"]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
        errors.append("oembed:" + type(exc).__name__)
    try:
        page = parse_youtube_live_html(getter(target["live_url"]))
        result["live"] = bool(page.get("live"))
        if page.get("title") and page["title"] not in ("", "YouTube"):
            result["title"] = result["title"] or page["title"]
        result["note"] = str(page.get("note") or result["note"])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        errors.append("live:" + type(exc).__name__)
        result["success"] = bool(result.get("title"))
        if not result["success"]:
            result["note"] = "YouTube check failed."
    if errors and result.get("success"):
        result["warnings"] = errors
    if not result["live"] and result.get("title") and result["note"] == "Not live.":
        result["note"] = "Not live. Broadcast on file: " + result["title"] + "."
    if persist:
        state = _load()
        state["youtube"] = result
        _save(state)
    return result


def level_pulse(*, min_interval: float = _YOUTUBE_MIN_INTERVAL_SEC) -> Dict[str, Any]:
    """Daemon hook. Refreshes the YouTube check when the last one is stale."""
    state = _load()
    youtube = state.get("youtube") if isinstance(state.get("youtube"), dict) else {}
    age = time.time() - float(youtube.get("ts") or 0)
    if youtube and age < min_interval:
        checked = youtube
        refreshed = False
    else:
        checked = check_youtube_live()
        refreshed = True
    directive = active_directive()
    live_label = "live" if checked.get("live") else "not live"
    vision = (directive.get("vision") or "unset")[:80]
    move = (directive.get("next_profit_move") or "unset")[:80]
    log = (
        f"[all-profit] level={directive.get('level')} "
        f"vision={vision} next={move} youtube={live_label}"
    )
    return {
        "success": True,
        "refreshed": refreshed,
        "log": log if refreshed else None,
        "youtube": checked,
        "directive": directive,
    }
