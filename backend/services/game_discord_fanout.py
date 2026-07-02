"""Off-request fan-out: game channel activity_events → Discord #game."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EVENTS = os.path.join(_BASE, "logs", "activity_events.jsonl")
_CURSOR = os.path.join(_BASE, "logs", "game_discord_cursor.json")

_GAME_EVENT_TYPES = frozenset({
    "battle_win",
    "battle_streak",
    "battle_tournament_join",
    "game_mn2_reward",
    "hunter_level_up",
    "compendium_complete",
    "shop_discord_promo_created",
})


def _load_cursor() -> int:
    if not os.path.isfile(_CURSOR):
        return 0
    try:
        with open(_CURSOR, "r", encoding="utf-8") as f:
            return int(json.load(f).get("line") or 0)
    except Exception:
        return 0


def _save_cursor(line: int) -> None:
    os.makedirs(os.path.dirname(_CURSOR), exist_ok=True)
    with _LOCK:
        tmp = _CURSOR + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"line": line}, f)
        os.replace(tmp, _CURSOR)


def _read_new_events() -> tuple[List[Dict[str, Any]], int]:
    if not os.path.isfile(_EVENTS):
        return [], _load_cursor()
    start = _load_cursor()
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
            if row.get("channel") != "game":
                continue
            if (row.get("type") or "") not in _GAME_EVENT_TYPES:
                continue
            rows.append(row)
    return rows, line_no


def _embed_for_event(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    base_url = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    et = row.get("type") or ""
    payload = row.get("payload") or {}

    if et == "battle_win":
        return {
            "embeds": [{
                "title": "Battle win",
                "description": f"**{payload.get('user_id') or 'Player'}** won a battle (+{payload.get('mn2') or 0} MN2)\n\n[Battle hub]({base_url}/battle/)",
                "color": 0x57F287,
            }],
        }
    if et == "compendium_complete":
        return {
            "embeds": [{
                "title": "Compendium milestone",
                "description": f"**{payload.get('title') or 'Milestone'}** reached.\n\n[Read rulebooks]({base_url}/compendium/?calm=1)",
                "color": 0x5865F2,
            }],
        }
    if et == "game_mn2_reward":
        return {
            "embeds": [{
                "title": "Game MN2 reward",
                "description": f"+**{payload.get('amount') or payload.get('mn2') or 0}** MN2 from game activity.\n\n[Game hub]({base_url}/game/)",
                "color": 0xFEE75C,
            }],
        }
    if et == "shop_discord_promo_created":
        return {
            "embeds": [{
                "title": "Shop promo",
                "description": f"Code **`{payload.get('code')}`** — redeem on-site.\n\n[Shop]({base_url}/shop/)",
                "color": 0x9B59B6,
            }],
        }
    return {
        "embeds": [{
            "title": et.replace("_", " ").title(),
            "description": (row.get("text") or "Game activity")[:500] + f"\n\n[Game hub]({base_url}/game/)",
            "color": 0x00CED1,
        }],
    }


def run_fanout(*, dry_run: bool = False) -> Dict[str, Any]:
    rows, end_line = _read_new_events()
    posted: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []
    from backend.services.discord_service import post_message

    for row in rows:
        et = row.get("type") or "event"
        ts = row.get("ts") or ""
        ref = (row.get("payload") or {}).get("ref") or (row.get("payload") or {}).get("battle_id")
        msg_id = f"game-fanout:{et}:{ref or ts}"
        embed = _embed_for_event(row)
        if embed is None:
            skipped.append(et)
            continue
        if dry_run:
            posted.append(f"dry:{msg_id}")
            continue
        result = post_message("game", embed, message_id=msg_id)
        if result.get("success"):
            posted.append(msg_id)
        else:
            errors.append(result.get("error") or "post_failed")

    if not dry_run:
        _save_cursor(end_line)

    return {
        "success": True,
        "processed": len(rows),
        "posted": len(posted),
        "skipped": len(skipped),
        "errors": errors,
        "cursor_line": end_line,
    }
