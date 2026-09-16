"""
House income aggregation — casino + arena reconcilable house edge.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List


def _root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _casino_db() -> str:
    log_dir = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_root(), "logs")
    return os.path.join(log_dir, "casino_ledger.db")


def _arena_state() -> Dict[str, Any]:
    path = os.path.join(_root(), "data", "arena_state.json")
    if not os.path.isfile(path):
        return {"events": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"events": {}}
    except Exception:
        return {"events": {}}


def summarize(since_hours: int = 24, venue: str = "all") -> Dict[str, Any]:
    since_hours = max(1, min(int(since_hours or 24), 24 * 30))
    since_iso = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%Y-%m-%dT%H:%M:%S")
    venue = (venue or "all").strip().lower()
    if venue not in ("all", "casino", "arena"):
        venue = "all"

    casino_by_currency: Dict[str, Dict[str, float]] = {}
    db_path = _casino_db()
    if venue in ("all", "casino") and os.path.isfile(db_path):
        try:
            conn = sqlite3.connect(db_path, timeout=3.0)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT currency,
                       SUM(bet) AS total_bet,
                       SUM(payout) AS total_payout,
                       SUM(net) AS total_net,
                       COUNT(*) AS bets
                FROM casino_bets
                WHERE created_at >= ?
                GROUP BY currency
                """,
                (since_iso,),
            )
            for row in cur.fetchall():
                c = str(row["currency"] or "coins")
                total_bet = float(row["total_bet"] or 0)
                total_payout = float(row["total_payout"] or 0)
                house = round(total_bet - total_payout, 8)
                casino_by_currency[c] = {
                    "total_bet": round(total_bet, 8),
                    "total_payout": round(total_payout, 8),
                    "house_edge": house,
                    "bets": int(row["bets"] or 0),
                }
            conn.close()
        except Exception:
            pass

    arena_house: Dict[str, float] = {}
    if venue in ("all", "arena"):
        state = _arena_state()
        for ev in (state.get("events") or {}).values():
            if not isinstance(ev, dict):
                continue
            c = str(ev.get("currency") or "coins")
            ht = float(ev.get("house_take") or 0)
            arena_house[c] = round(arena_house.get(c, 0) + ht, 8)

    total_house = {}
    if venue in ("all", "casino"):
        for c, v in casino_by_currency.items():
            total_house[c] = round(v.get("house_edge", 0) + (arena_house.get(c, 0) if venue == "all" else 0), 8)
    if venue in ("all", "arena"):
        for c, v in arena_house.items():
            if venue == "arena":
                total_house[c] = round(v, 8)
            elif c not in total_house:
                total_house[c] = round(v, 8)

    return {
        "success": True,
        "since_hours": since_hours,
        "since_iso": since_iso,
        "venue": venue,
        "casino": casino_by_currency if venue in ("all", "casino") else {},
        "arena_house_take": arena_house if venue in ("all", "arena") else {},
        "combined_house": total_house,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
