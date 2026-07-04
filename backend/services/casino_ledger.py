"""
DB-backed casino bet ledger (additive mirror).

The authoritative bet log remains logs/casino_bets.jsonl. This module mirrors
every settled bet into an indexed SQLite table so new, growth-sensitive reads
(e.g. the live winners ticker) don't re-scan the whole JSONL file. It uses only
the stdlib `sqlite3` — no new dependency — and every call is best-effort: a
failure here never blocks a bet.

This is the seed of the Phase-1 ledger migration in CASINO_EXPANSION_PLAN.md;
existing leaderboard/quest reads are intentionally left on JSONL for now.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOCK = threading.Lock()


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _db_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_ledger.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS casino_bets (
            bet_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            game TEXT NOT NULL,
            currency TEXT NOT NULL,
            bet REAL NOT NULL,
            payout REAL NOT NULL,
            net REAL NOT NULL,
            outcome TEXT,
            created_at TEXT NOT NULL,
            exclude_leaderboard INTEGER DEFAULT 0,
            details TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_casino_bets_created ON casino_bets (created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_casino_bets_user ON casino_bets (user_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_casino_bets_currency ON casino_bets (currency, created_at)")


def record(row: Dict[str, Any]) -> None:
    """Mirror a finalized bet row into the DB. Best-effort; never raises."""
    if not isinstance(row, dict) or not row.get("bet_id"):
        return
    try:
        with _LOCK:
            conn = _connect()
            try:
                _ensure_schema(conn)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO casino_bets
                        (bet_id, user_id, game, currency, bet, payout, net, outcome,
                         created_at, exclude_leaderboard, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(row.get("bet_id")),
                        str(row.get("user_id") or ""),
                        str(row.get("game") or ""),
                        str(row.get("currency") or "coins"),
                        float(row.get("bet") or 0),
                        float(row.get("payout") or 0),
                        float(row.get("net") or 0),
                        str(row.get("outcome") or ""),
                        str(row.get("created_at") or ""),
                        1 if row.get("exclude_leaderboard") else 0,
                        json.dumps(row.get("details") or {}, ensure_ascii=False),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
    except Exception:
        pass


def recent_wins(limit: int = 12, currency: Optional[str] = None) -> List[Dict[str, Any]]:
    """Recent winning bets for the live activity ticker (net > 0, leaderboard-eligible)."""
    safe_limit = max(1, min(int(limit or 12), 50))
    try:
        with _LOCK:
            conn = _connect()
            try:
                _ensure_schema(conn)
                params: List[Any] = []
                where = "net > 0 AND exclude_leaderboard = 0"
                if currency:
                    where += " AND currency = ?"
                    params.append(str(currency).lower())
                params.append(safe_limit)
                cur = conn.execute(
                    f"""
                    SELECT bet_id, user_id, game, currency, bet, payout, net, outcome, created_at, details
                    FROM casino_bets
                    WHERE {where}
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    params,
                )
                rows = [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()
        for r in rows:
            try:
                r["details"] = json.loads(r.get("details") or "{}")
            except Exception:
                r["details"] = {}
        return rows
    except Exception:
        return []


def _period_cutoff(period: str) -> Optional[str]:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    p = (period or "today").lower()
    if p == "today":
        return now.strftime("%Y-%m-%d")
    if p == "week":
        return (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
    return None


def daily_stats(days: int = 5, currency: Optional[str] = None) -> List[Dict[str, Any]]:
    """Per-day bet aggregates for the activity monitor (last N calendar days, UTC)."""
    from datetime import datetime, timedelta, timezone

    safe_days = max(1, min(int(days or 5), 30))
    now = datetime.now(timezone.utc)
    day_keys = [
        (now - timedelta(days=offset)).strftime("%Y-%m-%d")
        for offset in range(safe_days - 1, -1, -1)
    ]
    empty = {k: {"bets": 0, "wins": 0, "unique_players": 0, "jackpot_hits": 0, "total_net": 0.0} for k in day_keys}
    try:
        with _LOCK:
            conn = _connect()
            try:
                _ensure_schema(conn)
                params: List[Any] = []
                where = "1=1"
                if currency:
                    where += " AND currency = ?"
                    params.append(str(currency).lower())
                cutoff = (now - timedelta(days=safe_days - 1)).strftime("%Y-%m-%d")
                where += " AND substr(created_at, 1, 10) >= ?"
                params.append(cutoff)
                cur = conn.execute(
                    f"""
                    SELECT substr(created_at, 1, 10) AS day,
                           COUNT(*) AS bets,
                           SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins,
                           COUNT(DISTINCT user_id) AS unique_players,
                           SUM(CASE WHEN details LIKE '%"jackpot"%' THEN 1 ELSE 0 END) AS jackpot_hits,
                           SUM(net) AS total_net
                    FROM casino_bets
                    WHERE {where}
                    GROUP BY day
                    ORDER BY day ASC
                    """,
                    params,
                )
                for row in cur.fetchall():
                    day = str(row["day"])
                    if day not in empty:
                        continue
                    empty[day] = {
                        "bets": int(row["bets"] or 0),
                        "wins": int(row["wins"] or 0),
                        "unique_players": int(row["unique_players"] or 0),
                        "jackpot_hits": int(row["jackpot_hits"] or 0),
                        "total_net": float(row["total_net"] or 0),
                    }
            finally:
                conn.close()
    except Exception:
        pass
    return [{"day": day, **empty[day]} for day in day_keys]


def top_big_wins(days: int = 7, limit: int = 20, currency: Optional[str] = None) -> List[Dict[str, Any]]:
    """Top winning bets by payout multiplier over the last N days (ledger mirror)."""
    from datetime import datetime, timedelta, timezone

    safe_days = max(1, min(int(days or 7), 30))
    safe_limit = max(1, min(int(limit or 20), 50))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=safe_days)).isoformat().replace("+00:00", "Z")
    try:
        with _LOCK:
            conn = _connect()
            try:
                _ensure_schema(conn)
                params: List[Any] = [cutoff]
                where = "net > 0 AND bet > 0 AND exclude_leaderboard = 0 AND created_at >= ?"
                if currency:
                    where += " AND currency = ?"
                    params.append(str(currency).lower())
                params.append(safe_limit)
                cur = conn.execute(
                    f"""
                    SELECT bet_id, user_id, game, currency, bet, payout, net, outcome, created_at, details,
                           (payout / bet) AS multiplier
                    FROM casino_bets
                    WHERE {where}
                    ORDER BY multiplier DESC, net DESC
                    LIMIT ?
                    """,
                    params,
                )
                rows = [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()
        for r in rows:
            try:
                r["details"] = json.loads(r.get("details") or "{}")
            except Exception:
                r["details"] = {}
            bet = float(r.get("bet") or 0)
            payout = float(r.get("payout") or 0)
            r["multiplier"] = round(payout / bet, 2) if bet > 0 else 0.0
        return rows
    except Exception:
        return []


def user_bets_for_export(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Recent settled bets for a user — used by provably-fair CSV export."""
    safe_limit = max(1, min(int(limit or 100), 500))
    uid = str(user_id or "").strip()
    if not uid:
        return []
    try:
        with _LOCK:
            conn = _connect()
            try:
                _ensure_schema(conn)
                cur = conn.execute(
                    """
                    SELECT bet_id, user_id, game, currency, bet, payout, net, outcome, created_at, details
                    FROM casino_bets
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (uid, safe_limit),
                )
                rows = [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()
        for r in rows:
            try:
                r["details"] = json.loads(r.get("details") or "{}")
            except Exception:
                r["details"] = {}
        return rows
    except Exception:
        return []


def bet_count_since(day_prefix: str) -> int:
    """Count bets on or after a UTC date prefix (YYYY-MM-DD)."""
    try:
        with _LOCK:
            conn = _connect()
            try:
                _ensure_schema(conn)
                cur = conn.execute(
                    "SELECT COUNT(*) AS n FROM casino_bets WHERE substr(created_at, 1, 10) >= ?",
                    (day_prefix[:10],),
                )
                row = cur.fetchone()
                return int(row["n"] if row else 0)
            finally:
                conn.close()
    except Exception:
        return 0


def leaderboard_aggregate(period: str = "today", currency: str = "coins") -> Dict[str, Dict[str, float]]:
    """Aggregate net/wins/wagered per user from the DB mirror (leaderboard migration slice)."""
    currency = (currency or "coins").lower()
    cutoff_date = _period_cutoff(period)
    try:
        with _LOCK:
            conn = _connect()
            try:
                _ensure_schema(conn)
                params: List[Any] = [currency]
                where = "currency = ? AND exclude_leaderboard = 0"
                if cutoff_date:
                    if period == "today":
                        where += " AND created_at >= ?"
                        params.append(cutoff_date)
                    else:
                        where += " AND created_at >= ?"
                        params.append(cutoff_date)
                cur = conn.execute(
                    f"""
                    SELECT user_id,
                           SUM(net) AS net,
                           COUNT(*) AS bets,
                           SUM(bet) AS wagered,
                           SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins
                    FROM casino_bets
                    WHERE {where}
                    GROUP BY user_id
                    """,
                    params,
                )
                out: Dict[str, Dict[str, float]] = {}
                for row in cur.fetchall():
                    out[str(row["user_id"])] = {
                        "net": float(row["net"] or 0),
                        "bets": float(row["bets"] or 0),
                        "wagered": float(row["wagered"] or 0),
                        "wins": float(row["wins"] or 0),
                    }
                return out
            finally:
                conn.close()
    except Exception:
        return {}
