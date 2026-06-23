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
                    SELECT user_id, game, currency, bet, payout, net, outcome, created_at, details
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
