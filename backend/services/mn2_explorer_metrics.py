"""
Explorer API latency logging (P4 #187).

Appends one JSON line per request to logs/mn2_explorer_api.jsonl when
MN2_EXPLORER_METRICS is enabled (default on). Never raises.
"""
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_MAX_LOG_BYTES = 5_000_000
_PERCENTILES = (50, 95, 99)


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _log_path() -> str:
    return os.path.join(_base(), "logs", "mn2_explorer_api.jsonl")


def metrics_enabled() -> bool:
    return os.environ.get("MN2_EXPLORER_METRICS", "1").strip().lower() not in ("0", "false", "no", "off")


def record_api_call(path: str, status: int, duration_ms: float, method: str = "GET") -> None:
    if not metrics_enabled():
        return
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "path": path,
        "method": method,
        "status": int(status),
        "duration_ms": round(float(duration_ms), 2),
    }
    try:
        os.makedirs(os.path.dirname(_log_path()), exist_ok=True)
        with _LOCK:
            with open(_log_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            try:
                if os.path.getsize(_log_path()) > _MAX_LOG_BYTES:
                    _trim_log()
            except OSError:
                pass
    except Exception:
        pass


def _trim_log() -> None:
    path = _log_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        keep = lines[-2000:]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(keep)
        os.replace(tmp, path)
    except Exception:
        pass


def _percentile(values: List[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    idx = max(0, min(len(ordered) - 1, idx))
    return round(ordered[idx], 2)


def latency_summary(limit: int = 500) -> Dict[str, Any]:
    """Recent latency percentiles for ops dashboards."""
    rows: List[Dict[str, Any]] = []
    path = _log_path()
    if not os.path.isfile(path):
        return {"count": 0, "percentiles_ms": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return {"count": 0, "percentiles_ms": {}}
    if limit and len(rows) > limit:
        rows = rows[-limit:]
    durations = [float(r["duration_ms"]) for r in rows if r.get("duration_ms") is not None]
    return {
        "count": len(durations),
        "percentiles_ms": {f"p{int(p)}": _percentile(durations, p) for p in _PERCENTILES},
        "paths": _path_counts(rows),
    }


def _path_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows[-200:]:
        p = str(r.get("path") or "")
        out[p] = out.get(p, 0) + 1
    return out
