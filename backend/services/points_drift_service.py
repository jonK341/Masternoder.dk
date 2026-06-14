"""
File vs SQL unified points drift detection.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

_TOLERANCE = 1e-6
_SCALAR_KEYS = ("mn2_balance", "game_points", "xp_total", "generation_points", "casino_fiat_balance")


def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _points_dir() -> str:
    return os.path.join(_base_dir(), "logs", "unified_points")


def _file_scalars(user_id: str) -> Dict[str, float]:
    path = os.path.join(_points_dir(), f"{user_id}.json")
    if not os.path.isfile(path):
        return {}
    try:
        import json

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
    except Exception:
        return {}
    pts = raw.get("points") if isinstance(raw.get("points"), dict) else raw
    systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
    out: Dict[str, float] = {}
    for k in _SCALAR_KEYS:
        v = pts.get(k)
        if v is None:
            v = systems.get(k)
        if v is not None:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                pass
    if "xp_total" not in out and pts.get("xp_total") is not None:
        try:
            out["xp_total"] = float(pts.get("xp_total"))
        except (TypeError, ValueError):
            pass
    return out


def _db_scalars(user_id: str) -> Dict[str, float]:
    try:
        from backend.services.unified_points_database import unified_points_db

        res = unified_points_db.get_all_points(user_id)
        pts = res.get("points") if isinstance(res.get("points"), dict) else {}
        systems = res.get("systems") if isinstance(res.get("systems"), dict) else {}
        out: Dict[str, float] = {}
        for k in _SCALAR_KEYS:
            fv = _file_scalars(user_id).get(k)
            dv = pts.get(k)
            if dv is None:
                dv = systems.get(k)
            if fv is not None or dv is not None:
                out[k] = max(float(fv or 0), float(dv or 0))
        return out
    except Exception:
        return {}


def scan_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Compare raw file store vs DB-only read; report if file != db raw."""
    uid = str(user_id or "").strip()
    if not uid:
        return None
    file_vals = _file_scalars(uid)
    if not file_vals:
        return None

    db_raw: Dict[str, float] = {}
    try:
        from backend.services.unified_points_database import UnifiedPointsDatabase

        db = UnifiedPointsDatabase()
        raw = db._load_file_store(uid)
        pts = raw.get("points") if isinstance(raw.get("points"), dict) else raw
        systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
        for k in _SCALAR_KEYS:
            v = pts.get(k) if isinstance(pts, dict) else None
            if v is None:
                v = systems.get(k)
            if v is not None:
                db_raw[k] = float(v)
    except Exception:
        pass

    # Compare file on disk to what get_all_points merges — detect file vs SQL lag
    sql_vals: Dict[str, float] = {}
    try:
        from sqlalchemy import text
        from backend.services.unified_points_database import _unified_points_db_context

        with _unified_points_db_context():
            from src.app import db

            row = db.session.execute(
                text("SELECT total_xp FROM player_levels WHERE user_id = :uid LIMIT 1"),
                {"uid": uid},
            ).fetchone()
            if row and row[0] is not None:
                sql_vals["xp_total"] = float(row[0])
    except Exception:
        pass

    drifts: List[Dict[str, Any]] = []
    for k in _SCALAR_KEYS:
        fv = file_vals.get(k)
        sv = sql_vals.get(k)
        if fv is not None and sv is not None and abs(fv - sv) > _TOLERANCE:
            drifts.append({"field": k, "file": fv, "sql": sv, "delta": round(fv - sv, 8)})

    if not drifts:
        return None
    return {"user_id": uid, "drifts": drifts}


def scan_all(limit: int = 500) -> Dict[str, Any]:
    """Scan up to `limit` user point files for file/SQL drift."""
    pdir = _points_dir()
    alerts: List[Dict[str, Any]] = []
    try:
        names = sorted(fn for fn in os.listdir(pdir) if fn.endswith(".json"))[: max(1, limit)]
    except Exception:
        names = []
    for fn in names:
        uid = fn[:-5]
        hit = scan_user(uid)
        if hit:
            alerts.append(hit)
    return {
        "success": True,
        "scanned": len(names),
        "drift_count": len(alerts),
        "alerts": alerts,
    }
