"""Off-request fan-out: game channel activity_events → Discord #game (M8 / battle plan)."""
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
            et = row.get("type") or ""
            if et not in _GAME_EVENT_TYPES:
                continue
            rows.append(row)
    return rows, line_no


def _embed_for_event(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    base_url = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    battle_url = f"{base_url}/battle/"
    game_url = f"{base_url}/game/"
    quests_url = f"{base_url}/quests/"
    shop_url = f"{base_url}/shop/"
    et = row.get("type") or ""
    payload = row.get("payload") or {}

    if et == "battle_win":
        pts = payload.get("points_delta")
        difficulty = payload.get("difficulty") or "balanced"
        mode = payload.get("battle_mode") or "skirmish"
        return {
            "embeds": [{
                "title": "Battle victory",
                "description": (
                    f"A player won a **{difficulty}** {mode} duel "
                    f"({pts:+d} pts).\n\n"
                    f"[Play battles]({battle_url}) · [Hunters game]({game_url})\n\n"
                    "_Rewards and quests are claimed on-site with your linked account._"
                ),
                "color": 0x57F287,
            }],
        }

    if et == "battle_streak":
        streak = payload.get("streak") or 0
        return {
            "embeds": [{
                "title": f"Win streak ×{streak}",
                "description": (
                    f"Someone is on a **{streak}-win** battle streak.\n\n"
                    f"[Join the arena]({battle_url})"
                ),
                "color": 0xFEE75C,
            }],
        }

    if et == "battle_tournament_join":
        name = payload.get("tournament_name") or payload.get("tournament_id") or "Tournament"
        participants = payload.get("participants")
        extra = f" ({participants} joined)" if participants is not None else ""
        return {
            "embeds": [{
                "title": "Tournament signup",
                "description": (
                    f"**{name}**{extra}\n\n"
                    f"[View tournaments]({battle_url})"
                ),
                "color": 0x5865F2,
            }],
        }

    if et == "game_mn2_reward":
        amt = float(payload.get("amount") or 0)
        source = payload.get("source") or "game"
        if amt <= 0:
            return None
        return {
            "embeds": [{
                "title": "Game MN2 reward",
                "description": (
                    f"**+{amt:.4f} MN2** from {source}.\n\n"
                    f"[Game hub]({game_url}) · [Daily quests]({quests_url})"
                ),
                "color": 0x00D4FF,
            }],
        }

    if et == "hunter_level_up":
        level = payload.get("level")
        return {
            "embeds": [{
                "title": "Hunter level up",
                "description": (
                    f"A player reached **level {level}**.\n\n"
                    f"[Hunters game]({game_url})"
                ),
                "color": 0x9B59B6,
            }],
        }

    if et == "shop_discord_promo_created":
        code = payload.get("code")
        reward = payload.get("reward_label") or payload.get("reward_coins")
        return {
            "embeds": [{
                "title": "Shop promo code",
                "description": (
                    f"Use **`{code}`** in the shop for **{reward}**.\n\n"
                    f"[Open shop]({shop_url})\n\n"
                    "Affiliate disclosure: platform-operated promotion."
                ),
                "color": 0xE67E22,
            }],
        }

    if et == "compendium_complete":
        pages = payload.get("total_pages") or 25
        comp_url = f"{base_url}/compendium/?calm=1"
        return {
            "embeds": [{
                "title": "Compendium library complete",
                "description": (
                    f"A reader finished **{pages}/{pages}** rulebook pages.\n\n"
                    f"[Open calm library]({comp_url})"
                ),
                "color": 0x00FF88,
            }],
        }

    return None


def run_fanout(*, dry_run: bool = False) -> Dict[str, Any]:
    rows, end_line = _read_new_events()
    posted: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    from backend.services.discord_service import post_message

    for row in rows:
        et = row.get("type") or "event"
        ts = row.get("ts") or ""
        ref = (row.get("payload") or {}).get("battle_id") or (row.get("payload") or {}).get("reference")
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
