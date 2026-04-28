"""
Points Analytics Database Service
Read point_aggregates_daily and point_transactions for analytics. Safe when migration not run.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect


def _get_db():
    from src.db.models import db
    return db


def points_analytics_tables_exist() -> bool:
    """True if point_aggregates_daily exists (analytics migration run)."""
    try:
        return 'point_aggregates_daily' in inspect(_get_db().engine).get_table_names()
    except Exception:
        return False


def point_transactions_exist() -> bool:
    try:
        return 'point_transactions' in inspect(_get_db().engine).get_table_names()
    except Exception:
        return False


def get_analytics_daily(user_id: str, days: int = 30) -> Optional[List[Dict[str, Any]]]:
    """Daily aggregates for user. Returns None if tables not available."""
    if not points_analytics_tables_exist():
        return None
    try:
        db = _get_db()
        rows = db.session.execute(
            text("""
                SELECT aggregate_date, system_name, total_credits, total_debits, net_change, transaction_count
                FROM point_aggregates_daily
                WHERE user_id = :uid
                ORDER BY aggregate_date DESC
                LIMIT :lim
            """),
            {'uid': user_id, 'lim': days}
        ).fetchall()
        return [
            {
                'aggregate_date': str(r[0]),
                'system_name': r[1],
                'total_credits': float(r[2] or 0),
                'total_debits': float(r[3] or 0),
                'net_change': float(r[4] or 0),
                'transaction_count': int(r[5] or 0),
            }
            for r in rows
        ]
    except Exception:
        return None


def refresh_daily_aggregates(days: int = 7) -> bool:
    """Populate point_aggregates_daily from point_transactions for last N days. Returns True if run."""
    if not points_analytics_tables_exist() or not point_transactions_exist():
        return False
    try:
        db = _get_db()
        # SQLite: aggregate from point_transactions by date; use REPLACE or single-day refresh
        db.session.execute(
            text("""
                INSERT INTO point_aggregates_daily (user_id, aggregate_date, system_name, total_credits, total_debits, net_change, transaction_count)
                SELECT user_id, DATE(created_at), system_name,
                       SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END),
                       SUM(CASE WHEN transaction_type = 'debit' THEN amount ELSE 0 END),
                       SUM(CASE WHEN transaction_type = 'credit' THEN amount WHEN transaction_type = 'debit' THEN -amount ELSE 0 END),
                       COUNT(*)
                FROM point_transactions
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY user_id, DATE(created_at), system_name
                ON CONFLICT(user_id, aggregate_date, system_name) DO UPDATE SET
                    total_credits = excluded.total_credits,
                    total_debits = excluded.total_debits,
                    net_change = excluded.net_change,
                    transaction_count = excluded.transaction_count
            """)
        )
        db.session.commit()
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def get_analytics_summary(user_id: str, days: int = 30) -> Optional[Dict[str, Any]]:
    """Summary totals for user over last N days from point_transactions. Returns None if no table."""
    if not point_transactions_exist():
        return None
    try:
        db = _get_db()
        # Use fixed 30-day window to avoid dynamic SQL; caller can pass days for display
        r = db.session.execute(
            text("""
                SELECT COUNT(*), COALESCE(SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN transaction_type = 'debit' THEN amount ELSE 0 END), 0)
                FROM point_transactions
                WHERE user_id = :uid AND created_at >= datetime('now', '-30 days')
            """),
            {'uid': user_id}
        ).first()
        if not r:
            return {'transaction_count': 0, 'total_credits': 0, 'total_debits': 0, 'net': 0, 'days': 30}
        cnt, cred, deb = r[0] or 0, float(r[1] or 0), float(r[2] or 0)
        return {
            'transaction_count': cnt,
            'total_credits': cred,
            'total_debits': deb,
            'net': cred - deb,
            'days': 30,
        }
    except Exception:
        return None
