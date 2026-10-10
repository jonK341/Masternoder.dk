"""Read camgirls performer catalog from SQLite (009 migration) with JSON fallback."""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sqlite_path() -> str:
    url = (os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI") or "").strip()
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "", 1)
        if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
            return path
        return os.path.join(_ROOT, path)
    return os.path.join(_ROOT, "instance", "database.db")


def catalog_source_mode() -> str:
    return (os.environ.get("CAMGIRLS_CATALOG_SOURCE") or "auto").strip().lower()


def load_performers_from_db() -> Optional[List[Dict[str, Any]]]:
    if catalog_source_mode() == "json":
        return None
    path = _sqlite_path()
    if not os.path.isfile(path):
        return None
    try:
        conn = sqlite3.connect(path, timeout=3.0)
        conn.row_factory = sqlite3.Row
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='camgirls_performers'"
        ).fetchone():
            conn.close()
            return None
        rows = conn.execute(
            """SELECT performer_id, stage_name, bio, status, payload_json, payout_address
               FROM camgirls_performers ORDER BY performer_id"""
        ).fetchall()
        conn.close()
        if not rows:
            return None
        out: List[Dict[str, Any]] = []
        for row in rows:
            payload: Dict[str, Any] = {}
            raw = row["payload_json"]
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        payload = parsed
                except Exception:
                    payload = {}
            pid = str(row["performer_id"] or payload.get("id") or "")
            if not pid:
                continue
            merged = dict(payload)
            merged["id"] = pid
            merged["display_name"] = (
                merged.get("display_name") or row["stage_name"] or pid
            )
            if row["bio"]:
                merged["bio"] = row["bio"]
            status = (row["status"] or merged.get("status") or "active").lower()
            merged["active"] = status not in ("inactive", "disabled", "off")
            if row["payout_address"]:
                merged["payout_address"] = row["payout_address"]
            out.append(merged)
        return out
    except Exception:
        return None


def catalog_source_label() -> str:
    mode = catalog_source_mode()
    performers_json = os.path.join(_ROOT, "data", "camgirls_performers.json")
    has_json = os.path.isfile(performers_json)
    if mode == "json":
        return "json"
    if mode == "db":
        return "db" if load_performers_from_db() else "json"
    if has_json:
        try:
            with open(performers_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = data.get("performers") if isinstance(data, dict) else []
            if isinstance(rows, list) and len(rows) > 0:
                return "json"
        except Exception:
            pass
    return "db" if load_performers_from_db() else "json"
