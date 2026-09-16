"""Off-request fan-out: casino channel activity_events → Discord #casino (Gate S)."""
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
    "casino_big_win",
    "casino_jackpot_win",
    "casino_tournament_end",
    "casino_tournament_start",
    "casino_tournament_prize",
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
            if row.get("channel") != "casino":
                continue
            et = row.get("type") or ""
            if et not in _CASINO_EVENT_TYPES:
                continue
            rows.append(row)
    return rows, line_no


def _format_amount(amount: float, currency: str) -> str:
    if currency == "mn2":
        return f"{amount:.4f} MN2"
    if currency == "usd":
        return f"${amount:.2f}"
    return f"{int(amount)} coins"


def _embed_for_event(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from backend.services.casino_social_service import rg_footer

    base_url = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    casino_url = f"{base_url}/casino/"
    et = row.get("type") or ""
    payload = row.get("payload") or {}
    rg = rg_footer()

    if et == "casino_big_win":
        if not payload.get("share_ok"):
            return None
        player = payload.get("anonymized") or "Player"
        net = float(payload.get("net") or 0)
        currency = (payload.get("currency") or "coins").lower()
        game = payload.get("game") or "casino"
        return {
            "embeds": [{
                "title": "🎰 Casino big win",
                "description": (
                    f"**{player}** won **{_format_amount(net, currency)}** on **{game}**.\n\n"
                    f"[Play at the casino]({casino_url})\n\n"
                    f"_{rg}_"
                ),
                "color": 0x7C3AED,
            }],
        }

    if et == "casino_jackpot_win":
        player = payload.get("anonymized") if payload.get("share_ok") else "A lucky player"
        amount = float(payload.get("amount") or 0)
        currency = (payload.get("currency") or "coins").lower()
        reason = payload.get("reason") or "jackpot"
        return {
            "embeds": [{
                "title": "💰 Progressive jackpot hit!",
                "description": (
                    f"**{player}** took the **{_format_amount(amount, currency)}** "
                    f"jackpot ({reason}).\n\n"
                    f"[Spin for the next pool]({casino_url})\n\n"
                    f"_{rg}_"
                ),
                "color": 0xF59E0B,
            }],
        }

    if et == "casino_tournament_start":
        title = payload.get("title") or "Casino tournament"
        currency = (payload.get("currency") or "coins").lower()
        pool = float(payload.get("pool") or 0)
        end_at = payload.get("end_at") or ""
        return {
            "embeds": [{
                "title": "🏆 Tournament started",
                "description": (
                    f"**{title}** is live — **{_format_amount(pool, currency)}** prize pool.\n"
                    f"Ends: {end_at}\n\n"
                    f"[Join the cup]({casino_url}#tab-tournaments)\n\n"
                    f"_{rg}_"
                ),
                "color": 0x5865F2,
            }],
        }

    if et == "casino_tournament_end":
        title = payload.get("title") or "Casino tournament"
        currency = (payload.get("currency") or "coins").lower()
        pool = float(payload.get("pool") or 0)
        winners = int(payload.get("winner_count") or 0)
        return {
            "embeds": [{
                "title": "🏁 Tournament finished",
                "description": (
                    f"**{title}** — **{_format_amount(pool, currency)}** paid to "
                    f"top **{winners}** players.\n\n"
                    f"[Next tournament]({casino_url}#tab-tournaments)\n\n"
                    f"_{rg}_"
                ),
                "color": 0x22C55E,
            }],
        }

    if et == "casino_tournament_prize":
        if not payload.get("share_ok"):
            return None
        player = payload.get("anonymized") or "Player"
        prize = float(payload.get("prize") or 0)
        currency = (payload.get("currency") or "coins").lower()
        rank = int(payload.get("rank") or 0)
        return {
            "embeds": [{
                "title": "🥇 Tournament prize",
                "description": (
                    f"**{player}** placed **#{rank}** and won "
                    f"**{_format_amount(prize, currency)}**.\n\n"
                    f"[Casino tournaments]({casino_url}#tab-tournaments)\n\n"
                    f"_{rg}_"
                ),
                "color": 0xEAB308,
            }],
        }

    return None


def run_fanout(*, dry_run: bool = False) -> Dict[str, Any]:
    """Process new casino channel activity events → Discord #casino."""
    rows, end_line = _read_new_events()
    posted: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    from backend.services.discord_service import post_message

    for row in rows:
        et = row.get("type") or "event"
        ts = row.get("ts") or ""
        payload = row.get("payload") or {}
        ref = payload.get("bet_id") or payload.get("tournament_id") or ts
        msg_id = f"casino-fanout:{et}:{ref}"
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
