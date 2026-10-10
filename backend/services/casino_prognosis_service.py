"""
Casino future sights — battle-linked prognoses, streaks, and trend signals.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _casino_db() -> str:
    log_dir = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")
    return os.path.join(log_dir, "casino_ledger.db")


def _ledger_streaks(user_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    db_path = _casino_db()
    if not os.path.isfile(db_path):
        return {"recent_bets": 0, "wins": 0, "losses": 0, "streak": 0, "hot_game": None}
    try:
        conn = sqlite3.connect(db_path, timeout=3.0)
        conn.row_factory = sqlite3.Row
        q = "SELECT game, outcome, net FROM casino_bets"
        params: List[Any] = []
        if user_id:
            q += " WHERE user_id = ?"
            params.append(user_id)
        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(5, min(int(limit or 50), 200)))
        rows = conn.execute(q, params).fetchall()
        conn.close()
    except Exception:
        return {"recent_bets": 0, "wins": 0, "losses": 0, "streak": 0, "hot_game": None}

    wins = sum(1 for r in rows if str(r["outcome"] or "").lower() == "win")
    losses = len(rows) - wins
    streak = 0
    if rows:
        first = str(rows[0]["outcome"] or "").lower()
        for r in rows:
            if str(r["outcome"] or "").lower() == first:
                streak += 1
            else:
                break
        streak = streak if first == "win" else -streak
    games = Counter(str(r["game"] or "") for r in rows if r["game"])
    hot = games.most_common(1)[0][0] if games else None
    return {
        "recent_bets": len(rows),
        "wins": wins,
        "losses": losses,
        "streak": streak,
        "hot_game": hot,
    }


def battle_outcome_prognosis(difficulty: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_service as casino

    dist = casino.get_battle_outcome_distribution(difficulty=difficulty)
    pcts = dist.get("percentages") or {}
    best = max(pcts.items(), key=lambda kv: float(kv[1] or 0)) if pcts else ("win", 33.0)
    return {
        "kind": "battle_outcome",
        "distribution": pcts,
        "payout_multipliers": dist.get("payout_multipliers") or {},
        "signal": best[0],
        "confidence": round(float(best[1] or 0) / 100.0, 3),
        "window_label": dist.get("window_label"),
        "difficulty": dist.get("difficulty"),
        "play_hint": f"Lean {best[0]} — {best[1]}% of recent battles in window.",
    }


def rps_prognosis(difficulty: Optional[str] = None, player_move: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_service as casino

    dist = casino.get_battle_rps_distribution(difficulty=difficulty, player_move=player_move)
    pcts = dist.get("percentages") or {}
    best = max(pcts.items(), key=lambda kv: float(kv[1] or 0)) if pcts else ("rock", 33.0)
    return {
        "kind": "rps_distribution",
        "distribution": pcts,
        "payout_multipliers": dist.get("payout_multipliers") or {},
        "signal": best[0],
        "confidence": round(float(best[1] or 0) / 100.0, 3),
        "window_label": dist.get("window_label"),
        "signal_label": dist.get("signal_label"),
        "play_hint": f"Meta skew: {best[0]} at {best[1]}% — bet distribution or counter-pick.",
    }


def game_trend_prognosis(game_id: str, since_hours: int = 24) -> Dict[str, Any]:
    gid = (game_id or "coin_flip").strip().lower()
    db_path = _casino_db()
    since_iso = (datetime.now(timezone.utc) - timedelta(hours=max(1, min(since_hours, 168)))).strftime("%Y-%m-%dT%H:%M:%S")
    wins = losses = 0
    if os.path.isfile(db_path):
        try:
            conn = sqlite3.connect(db_path, timeout=3.0)
            cur = conn.execute(
                """
                SELECT outcome, COUNT(*) AS c FROM casino_bets
                WHERE game = ? AND created_at >= ?
                GROUP BY outcome
                """,
                (gid, since_iso),
            )
            for row in cur.fetchall():
                if str(row[0] or "").lower() == "win":
                    wins = int(row[1] or 0)
                else:
                    losses += int(row[1] or 0)
            conn.close()
        except Exception:
            pass
    total = wins + losses or 1
    win_rate = round(wins / total * 100, 1)
    return {
        "kind": "game_trend",
        "game_id": gid,
        "since_hours": since_hours,
        "sample_bets": total,
        "platform_win_rate_percent": win_rate,
        "play_hint": (
            f"Players won {win_rate}% on {gid} in last {since_hours}h — variance, not a guarantee."
        ),
    }


def build_prognosis_hub(*, user_id: Optional[str] = None, difficulty: Optional[str] = None) -> Dict[str, Any]:
    streaks = _ledger_streaks(user_id)
    battle = battle_outcome_prognosis(difficulty=difficulty)
    rps = rps_prognosis(difficulty=difficulty)
    hot_game = streaks.get("hot_game") or "coin_flip"
    trend = game_trend_prognosis(hot_game)
    sights = [
        {"id": "battle_meta", "title": "Battle outcome sight", **battle},
        {"id": "rps_meta", "title": "RPS meta sight", **rps},
        {"id": "hot_game_trend", "title": f"Trend: {hot_game}", **trend},
    ]
    if user_id:
        sights.append(
            {
                "id": "your_streak",
                "title": "Your streak sight",
                "kind": "user_streak",
                **streaks,
                "play_hint": (
                    f"Current streak {streaks.get('streak', 0)} — "
                    + ("consider smaller bets." if streaks.get("streak", 0) < 0 else "ride carefully.")
                ),
            }
        )
    return {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "future_sights": sights,
        "prognoses": sights,
        "streaks": streaks,
    }
