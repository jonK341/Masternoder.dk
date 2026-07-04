"""
Ops read API for MN2 withdrawal risk log + sybil cluster summary.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_PATH = os.path.join(_BASE_DIR, "logs", "mn2_withdrawal_risk.jsonl")


def _parse_ts(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        s = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def read_withdrawal_assessments(limit: int = 100) -> List[Dict[str, Any]]:
    if not os.path.isfile(_LOG_PATH):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return list(reversed(rows[-max(1, min(limit, 500)) :]))


def risk_summary() -> Dict[str, Any]:
    rows = read_withdrawal_assessments(limit=500)
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    level_all = Counter()
    level_24h = Counter()
    level_7d = Counter()
    high_users: List[str] = []

    for r in rows:
        lvl = (r.get("level") or "unknown").lower()
        level_all[lvl] += 1
        ts = _parse_ts(r.get("ts") or "")
        if ts and ts >= since_24h:
            level_24h[lvl] += 1
        if ts and ts >= since_7d:
            level_7d[lvl] += 1
        if lvl == "high":
            uid = (r.get("user_id") or "").strip()
            if uid and uid not in high_users:
                high_users.append(uid)

    cfg = {}
    try:
        cfg_path = os.path.join(_BASE_DIR, "data", "mn2_config.json")
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = (json.load(f) or {}).get("withdrawal_risk") or {}
    except Exception:
        pass

    return {
        "success": True,
        "log_path": "logs/mn2_withdrawal_risk.jsonl",
        "total_logged": len(rows),
        "by_level_all": dict(level_all),
        "by_level_24h": dict(level_24h),
        "by_level_7d": dict(level_7d),
        "recent_high_users": high_users[:20],
        "config": cfg,
        "generated_at": now.isoformat().replace("+00:00", "Z"),
    }


def sybil_summary(limit: int = 50, min_score: float = 0.35) -> Dict[str, Any]:
    try:
        from backend.services.mn2_sybil_graph import ops_clusters

        return ops_clusters(min_score=min_score, limit=limit)
    except Exception as exc:
        return {"success": False, "error": str(exc), "clusters": []}
