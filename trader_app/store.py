"""Local persistence for the trader app: PnL/equity history snapshots + CSV export.

Small, dependency-free JSON-lines store kept next to the app so the dashboard can render
sparklines and export history without a database.
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

_STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".state")
_HISTORY_PATH = os.path.join(_STATE_DIR, "history.jsonl")
_ALERTS_PATH = os.path.join(_STATE_DIR, "alerts.jsonl")
_MAX_ROWS = 1000


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure() -> None:
    os.makedirs(_STATE_DIR, exist_ok=True)


def _append(path: str, row: Dict[str, Any]) -> None:
    _ensure()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
    # Trim occasionally to keep files bounded.
    try:
        if os.path.getsize(path) > 400_000:
            rows = _read(path)[-_MAX_ROWS:]
            with open(path, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, default=str) + "\n")
    except OSError:
        pass


def _read(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


_last_snap = [0.0]


def record_snapshot(total_usd: float, realized: float, projected_daily: float,
                    *, min_interval_s: int = 20) -> None:
    """Append an equity/PnL snapshot, throttled to avoid flooding the file."""
    now = time.time()
    if now - _last_snap[0] < min_interval_s:
        return
    _last_snap[0] = now
    _append(_HISTORY_PATH, {"ts": _iso(), "total_usd": round(float(total_usd or 0), 4),
                            "realized": round(float(realized or 0), 6),
                            "projected_daily": round(float(projected_daily or 0), 4)})


def history(limit: int = 200) -> List[Dict[str, Any]]:
    return _read(_HISTORY_PATH)[-int(limit or 200):]


def record_alert(kind: str, message: str, level: str = "info") -> None:
    _append(_ALERTS_PATH, {"ts": _iso(), "kind": kind, "message": message, "level": level})


def alerts(limit: int = 50) -> List[Dict[str, Any]]:
    return _read(_ALERTS_PATH)[-int(limit or 50):][::-1]


def to_csv(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()
