"""
MN2 network stats history + health alerting (explorer Phase E4 #1/#3).

- record_snapshot(overview): throttled append of a network-overview snapshot to
  data/mn2_network_history.jsonl, used for sparklines on /explorer.
- Edge-triggered alerts when the daemon stops minting (staking_active True->False)
  or the chain height stalls; written to logs/mn2_network_alerts.jsonl and,
  best-effort, to an admin notification if MN2_ALERT_USER_ID is set.
- get_history()/get_alerts() expose recent data for the API.

Best-effort and never raises into the request path.
"""
import os
import json
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()

_SNAPSHOT_MIN_INTERVAL_SEC = 600      # at most one snapshot / 10 min
_HISTORY_MAX_ROWS = 5000              # keep file bounded
_STALL_SECONDS = 1800                 # height unchanged this long => stall alert
_STALL_MIN_SAMPLES = 3                # require at least N samples in the window

# Fields captured per snapshot (numeric/booleans only).
_SNAPSHOT_KEYS = (
    "block_height", "mn2_usd_price", "difficulty", "network_hashps",
    "staking_weight", "masternode_count", "pool_total_staked",
    "connections", "mempool_tx",
)


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _history_path() -> str:
    return os.path.join(_base(), "data", "mn2_network_history.jsonl")


def _alerts_path() -> str:
    return os.path.join(_base(), "logs", "mn2_network_alerts.jsonl")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).isoformat().replace("+00:00", "Z")


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _read_rows(path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    rows: List[Dict[str, Any]] = []
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
        return []
    if limit is not None and len(rows) > limit:
        rows = rows[-limit:]
    return rows


def _staking_active(overview: Dict[str, Any]) -> Optional[bool]:
    sh = overview.get("staking_health") if isinstance(overview, dict) else None
    if isinstance(sh, dict):
        return sh.get("staking_active")
    return None


def _detect_alert(prev: Optional[Dict[str, Any]], cur: Dict[str, Any], recent: List[Dict[str, Any]]) -> Optional[str]:
    """Return an alert type if a NEW problem condition is detected this snapshot, else None.

    Edge-triggered relative to the previous snapshot's recorded alert so we don't spam.
    """
    prev_alert = (prev or {}).get("alert")

    # staking stopped: previous active, now explicitly inactive
    prev_active = (prev or {}).get("staking_active")
    cur_active = cur.get("staking_active")
    if prev_active is True and cur_active is False:
        return "staking_stopped"

    # height stall: enough samples within the window all at the same height as now
    cutoff = _now() - timedelta(seconds=_STALL_SECONDS)
    window = [r for r in recent if (_parse_iso(r.get("ts")) or _now()) >= cutoff]
    window.append(cur)
    h = cur.get("block_height")
    if (
        h is not None
        and len(window) >= _STALL_MIN_SAMPLES
        and all(r.get("block_height") == h for r in window)
    ):
        if prev_alert != "height_stall":  # edge-trigger
            return "height_stall"

    return None


def _emit_alert(alert_type: str, cur: Dict[str, Any]) -> None:
    rec = {
        "ts": _iso(),
        "type": alert_type,
        "block_height": cur.get("block_height"),
        "staking_active": cur.get("staking_active"),
        "message": {
            "staking_stopped": "MN2 daemon staking stopped (was active, now inactive). Realized yield will be 0 until it resumes.",
            "height_stall": "MN2 chain height has not advanced for >= %d min. Daemon may be stuck or desynced." % (_STALL_SECONDS // 60),
        }.get(alert_type, alert_type),
    }
    try:
        os.makedirs(os.path.dirname(_alerts_path()), exist_ok=True)
        with open(_alerts_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass
    # Best-effort admin notification (no-op if not configured).
    admin = (os.environ.get("MN2_ALERT_USER_ID") or "").strip()
    if admin:
        try:
            from backend.services.user_engagement import add_notification
            add_notification(admin, "MN2 staking alert", rec["message"], category="mn2_alert", metadata=rec)
        except Exception:
            pass


def record_snapshot(overview: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    """Throttled append of a network snapshot; runs alert detection. Best-effort."""
    if not isinstance(overview, dict):
        return {"recorded": False, "reason": "bad_overview"}
    with _LOCK:
        try:
            existing = _read_rows(_history_path(), limit=_HISTORY_MAX_ROWS)
            prev = existing[-1] if existing else None
            if not force and prev is not None:
                last_ts = _parse_iso(prev.get("ts"))
                if last_ts and (_now() - last_ts).total_seconds() < _SNAPSHOT_MIN_INTERVAL_SEC:
                    return {"recorded": False, "reason": "throttled"}

            row: Dict[str, Any] = {"ts": _iso()}
            for k in _SNAPSHOT_KEYS:
                row[k] = overview.get(k)
            row["staking_active"] = _staking_active(overview)

            alert = _detect_alert(prev, row, existing)
            row["alert"] = alert
            if alert:
                _emit_alert(alert, row)

            combined = existing + [row]
            if len(combined) > _HISTORY_MAX_ROWS:
                combined = combined[-_HISTORY_MAX_ROWS:]
            os.makedirs(os.path.dirname(_history_path()), exist_ok=True)
            tmp = _history_path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                for r in combined:
                    f.write(json.dumps(r) + "\n")
            os.replace(tmp, _history_path())
            return {"recorded": True, "alert": alert}
        except Exception as exc:
            return {"recorded": False, "reason": str(exc)}


def get_history(hours: float = 24.0, limit: int = 500) -> List[Dict[str, Any]]:
    """Recent snapshots within `hours`, oldest-first, capped at `limit`."""
    rows = _read_rows(_history_path(), limit=_HISTORY_MAX_ROWS)
    if hours and hours > 0:
        cutoff = _now() - timedelta(hours=hours)
        rows = [r for r in rows if (_parse_iso(r.get("ts")) or _now()) >= cutoff]
    if limit and len(rows) > limit:
        rows = rows[-limit:]
    return rows


def get_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """Most recent alerts, newest-first."""
    rows = _read_rows(_alerts_path(), limit=max(1, min(int(limit or 20), 200)))
    return list(reversed(rows))
