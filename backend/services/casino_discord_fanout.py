"""Off-request cron fan-out: activity_events.jsonl → Discord #casino (Gate S)."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EVENTS = os.path.join(_BASE, "logs", "activity_events.jsonl")
_CURSOR = os.path.join(_BASE, "logs", "casino_discord_cursor.json")

_CASINO_EVENT_TYPES = frozenset({
    "casino_jackpot_win",
    "casino_big_win",
    "casino_tournament_end",
    "casino_tournament_prize",
    "casino_mn2_promo",
    "casino_rg_reminder",
    "casino_discord_promo_created",
    "casino_agent_play",
})


def _load_cursor() -> int:
    if not os.path.isfile(_CURSOR):
        return 0
    try:
        with open(_CURSOR, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("line") or 0)
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
            if row.get("channel") != "casino":
                continue
            et = row.get("type") or ""
            if et not in _CASINO_EVENT_TYPES:
                continue
            rows.append(row)
    return rows, line_no


def _embed_for_event(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from backend.services.casino_social_service import rg_footer

    et = row.get("type") or ""
    payload = row.get("payload") or {}
    base_url = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    casino_url = f"{base_url}/casino/"

    if et == "casino_jackpot_win":
        if not payload.get("share_ok"):
            return None
        return {
            "embeds": [{
                "title": "Jackpot win highlight",
                "description": (
                    f"**{payload.get('anonymized') or 'Player'}** hit the progressive "
                    f"**{(payload.get('currency') or '').upper()}** jackpot for **{payload.get('amount')}**!\n\n"
                    f"[Play at the casino]({casino_url})\n\n_{rg_footer()}_"
                ),
                "color": 0xFFD700,
            }],
        }

    if et == "casino_big_win":
        if not payload.get("share_ok"):
            return None
        return {
            "embeds": [{
                "title": "Big win highlight",
                "description": (
                    f"**{payload.get('anonymized') or 'Player'}** won **{payload.get('net')} "
                    f"{(payload.get('currency') or '').upper()}** net on **{payload.get('game') or 'casino'}**.\n\n"
                    f"[Play at the casino]({casino_url})\n\n_{rg_footer()}_"
                ),
                "color": 0x57F287,
            }],
        }

    if et == "casino_tournament_end":
        return {
            "embeds": [{
                "title": f"Tournament complete — {payload.get('title') or 'Tournament'}",
                "description": (
                    f"Prizes from a **{payload.get('pool')} {(payload.get('currency') or '').upper()}** pool awarded.\n\n"
                    f"[Join the next tournament]({casino_url})\n\n_{rg_footer()}_"
                ),
                "color": 0x5865F2,
            }],
        }

    if et == "casino_tournament_prize":
        if not payload.get("share_ok"):
            return None
        return {
            "embeds": [{
                "title": "Tournament podium",
                "description": (
                    f"**{payload.get('anonymized') or 'Player'}** finished **#{payload.get('rank')}** "
                    f"and won **{payload.get('prize')} {(payload.get('currency') or '').upper()}**.\n\n"
                    f"[Compete in tournaments]({casino_url})\n\n_{rg_footer()}_"
                ),
                "color": 0xEB459E,
            }],
        }

    if et == "casino_mn2_promo":
        return {
            "embeds": [{
                "title": payload.get("title") or "MN2 casino promo",
                "description": f"{payload.get('summary') or ''}\n\n[Deposit MN2 & play]({casino_url})\n\n_{rg_footer()}_",
                "color": 0xFEE75C,
            }],
        }

    if et == "casino_rg_reminder":
        return {
            "embeds": [{
                "title": "Responsible gambling",
                "description": f"{payload.get('summary') or rg_footer()}\n\n[Set limits in profile]({base_url}/profile/)",
                "color": 0xED4245,
            }],
        }

    if et == "casino_discord_promo_created":
        return {
            "embeds": [{
                "title": "Discord-exclusive promo",
                "description": (
                    f"Use code **`{payload.get('code')}`** for **{payload.get('reward_coins')} bonus coins**.\n\n"
                    f"[Redeem at the casino]({casino_url})\n\n_{rg_footer()}_"
                ),
                "color": 0x9B59B6,
            }],
        }

    if et == "casino_agent_play":
        tag = "🤖 AI" if payload.get("used_ai") else "🎲 Bot"
        return {
            "embeds": [{
                "title": f"{tag} arena — {payload.get('agent_id') or 'agent'}",
                "description": (
                    f"_{payload.get('spectator_line') or payload.get('reasoning') or 'Agent placed a bet.'}_\n\n"
                    f"Game: **{payload.get('game') or 'casino'}** · Net: **{payload.get('net')}**\n\n"
                    f"[Watch the leaderboard]({casino_url})\n\n_{rg_footer()}_"
                ),
                "color": 0x00CED1,
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
        bet_id = (row.get("payload") or {}).get("bet_id")
        msg_id = f"casino-fanout:{et}:{bet_id or ts}"
        embed = _embed_for_event(row)
        if embed is None:
            skipped.append(et)
            continue
        if dry_run:
            posted.append(f"dry:{msg_id}")
            continue
        result = post_message("casino", embed, message_id=msg_id)
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
