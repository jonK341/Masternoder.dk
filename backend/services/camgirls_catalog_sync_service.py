"""Sync camgirls performer catalog from JSON into SQLite (Phase 4 DB catalog)."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.camgirls_catalog_db_service import _sqlite_path, load_performers_from_db

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PERFORMERS_JSON = os.path.join(_ROOT, "data", "camgirls_performers.json")

_CREATE_PERFORMERS_SQL = """
CREATE TABLE IF NOT EXISTS camgirls_performers (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  performer_id  TEXT    NOT NULL UNIQUE,
  stage_name    TEXT,
  user_ref      TEXT,
  status        TEXT,
  payout_address TEXT,
  paypal_email  TEXT,
  rating        REAL,
  followers     INTEGER NOT NULL DEFAULT 0,
  bio           TEXT,
  payload_json  TEXT,
  version       TEXT    NOT NULL DEFAULT '11.0.0',
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP
);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _connect() -> sqlite3.Connection:
    path = _sqlite_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_performers_table(conn: Optional[sqlite3.Connection] = None) -> bool:
    own = conn is None
    if own:
        conn = _connect()
    try:
        conn.execute(_CREATE_PERFORMERS_SQL)
        conn.commit()
        return True
    finally:
        if own and conn:
            conn.close()


def _performer_status(row: Dict[str, Any]) -> str:
    if row.get("active") is False:
        return "inactive"
    return str(row.get("status") or "active")


def upsert_performer_db(row: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> bool:
    if not isinstance(row, dict):
        return False
    pid = str(row.get("id") or row.get("performer_id") or "").strip()
    if not pid:
        return False
    own = conn is None
    if own:
        conn = _connect()
        ensure_performers_table(conn)
    payload = dict(row)
    payload["id"] = pid
    stage_name = str(row.get("display_name") or row.get("stage_name") or pid)
    bio = row.get("bio")
    payout = row.get("payout_address") or row.get("address")
    try:
        conn.execute(
            """INSERT INTO camgirls_performers
                 (performer_id, stage_name, user_ref, status, payout_address, paypal_email,
                  rating, followers, bio, payload_json, version, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(performer_id) DO UPDATE SET
                 stage_name=excluded.stage_name,
                 user_ref=COALESCE(excluded.user_ref, camgirls_performers.user_ref),
                 status=excluded.status,
                 payout_address=COALESCE(excluded.payout_address, camgirls_performers.payout_address),
                 paypal_email=COALESCE(excluded.paypal_email, camgirls_performers.paypal_email),
                 rating=COALESCE(excluded.rating, camgirls_performers.rating),
                 followers=COALESCE(excluded.followers, camgirls_performers.followers),
                 bio=COALESCE(excluded.bio, camgirls_performers.bio),
                 payload_json=excluded.payload_json,
                 updated_at=excluded.updated_at""",
            (
                pid,
                stage_name,
                row.get("user_id") or row.get("user_ref"),
                _performer_status(row),
                payout,
                row.get("paypal_email"),
                row.get("rating"),
                int(row.get("followers") or 0),
                bio,
                json.dumps(payload, default=str),
                str(row.get("version") or "11.0.0"),
                _utcnow(),
                _utcnow(),
            ),
        )
        if own:
            conn.commit()
        return True
    except Exception:
        return False
    finally:
        if own and conn:
            conn.close()


def _load_json_performers(path: Optional[str] = None) -> List[Dict[str, Any]]:
    json_path = path or _PERFORMERS_JSON
    if not os.path.isfile(json_path):
        return []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    rows = data.get("performers") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]


def sync_json_catalog_to_db(
    *,
    json_path: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    rows = _load_json_performers(json_path)
    if not rows:
        return {"success": False, "error": "no_performers_in_json", "synced": 0}
    if dry_run:
        return {"success": True, "dry_run": True, "would_sync": len(rows)}
    conn = _connect()
    ensure_performers_table(conn)
    synced = 0
    errors: List[str] = []
    try:
        for row in rows:
            if upsert_performer_db(row, conn=conn):
                synced += 1
            else:
                pid = row.get("id") or "?"
                errors.append(str(pid))
        conn.commit()
    finally:
        conn.close()
    db_count = len(load_performers_from_db() or [])
    return {
        "success": synced > 0 and not errors,
        "synced": synced,
        "json_rows": len(rows),
        "db_active_rows": db_count,
        "errors": errors,
        "sqlite_path": _sqlite_path(),
    }


def catalog_db_stats() -> Dict[str, Any]:
    path = _sqlite_path()
    if not os.path.isfile(path):
        return {"success": True, "table": False, "count": 0, "sqlite_path": path}
    try:
        conn = _connect()
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='camgirls_performers'"
        ).fetchone():
            conn.close()
            return {"success": True, "table": False, "count": 0, "sqlite_path": path}
        count = conn.execute("SELECT COUNT(*) FROM camgirls_performers").fetchone()[0]
        conn.close()
        return {"success": True, "table": True, "count": int(count), "sqlite_path": path}
    except Exception as exc:
        return {"success": False, "error": str(exc), "sqlite_path": path}
