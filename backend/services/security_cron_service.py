"""Security cron sweep — conservation, drift, deposits, risk, anomaly (Phase 9)."""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ACTIVITY = os.path.join(_BASE, "logs", "activity_events.jsonl")
_RISK_LOG = os.path.join(_BASE, "logs", "mn2_withdrawal_risk.jsonl")

PRESETS = {
    "full": [
        "conservation",
        "points_drift",
        "deposit_scanner",
        "treasury_reconcile",
        "withdrawal_risk",
        "anomaly",
        "session_cleanup",
        "backup",
        "agent_kill_switch",
    ],
    "sweep": [
        "conservation",
        "points_drift",
        "deposit_scanner",
        "treasury_reconcile",
        "withdrawal_risk",
        "anomaly",
        "agent_kill_switch",
    ],
    "risk": ["withdrawal_risk", "anomaly", "agent_kill_switch"],
    "reconcile": ["conservation", "points_drift", "treasury_reconcile"],
    "backup": ["backup"],
}


def list_presets() -> Dict[str, Any]:
    return {"success": True, "presets": {k: list(v) for k, v in PRESETS.items()}}


def _iso_cutoff(hours: int = 24) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=max(1, hours))


def _parse_ts(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None


def check_withdrawal_risk(*, limit: int = 50) -> Dict[str, Any]:
    """Summarize recent withdrawal risk assessments (elevated/high)."""
    limit = max(1, min(int(limit or 50), 500))
    if not os.path.isfile(_RISK_LOG):
        return {"success": True, "count": 0, "elevated": 0, "high": 0, "recent": []}
    rows: List[dict] = []
    try:
        with open(_RISK_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    recent = rows[-limit:]
    elevated = sum(1 for r in recent if str(r.get("level") or r.get("risk_level") or "").lower() == "elevated")
    high = sum(1 for r in recent if str(r.get("level") or r.get("risk_level") or "").lower() == "high")
    return {
        "success": True,
        "count": len(recent),
        "elevated": elevated,
        "high": high,
        "recent": recent[-10:],
    }


def check_anomaly(*, hours: int = 24, threshold: int = 50) -> Dict[str, Any]:
    """Flag users with excessive MN2 earn events in the lookback window."""
    if not os.path.isfile(_ACTIVITY):
        return {"success": True, "flagged": [], "threshold": threshold}
    cutoff = _iso_cutoff(hours)
    counts: Counter = Counter()
    earn_types = {
        "game_mn2_reward",
        "generator_mn2_credit",
        "debugger_quiz",
        "quest_complete",
        "quest_reward",
    }
    try:
        with open(_ACTIVITY, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                dt = _parse_ts(row.get("ts") or row.get("timestamp") or "")
                if not dt or dt < cutoff:
                    continue
                et = row.get("type") or row.get("event") or row.get("kind") or ""
                if et in earn_types:
                    uid = (row.get("user_id") or "").strip()
                    if uid:
                        counts[uid] += 1
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    flagged = [
        {"user_id": uid, "earn_events": n}
        for uid, n in counts.most_common()
        if n > threshold
    ]
    # Soft-flag via account_security when available (never auto-freeze money).
    for row in flagged[:20]:
        try:
            from backend.services.account_security_service import flag_user
            flag_user(row["user_id"], reason="earn_velocity", metadata=row)
        except Exception:
            pass
    return {
        "success": True,
        "flagged": flagged,
        "threshold": threshold,
        "hours": hours,
        "flagged_count": len(flagged),
    }


def check_session_cleanup(*, max_age_hours: int = 72) -> Dict[str, Any]:
    """Best-effort expired session / temp identifier cleanup."""
    cleaned = 0
    errors: List[str] = []
    ident_dir = os.path.join(_BASE, "logs", "user_identifiers")
    if os.path.isdir(ident_dir):
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(max_age_hours or 72)))
        for name in os.listdir(ident_dir):
            if not (name.startswith("temp_") or name.startswith("anon_")):
                continue
            path = os.path.join(ident_dir, name)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
                if mtime < cutoff:
                    os.remove(path)
                    cleaned += 1
            except Exception as exc:
                errors.append(str(exc)[:120])
    try:
        from backend.services.login_security_service import cleanup_expired_sessions
        extra = cleanup_expired_sessions(max_age_hours=max_age_hours)
        if isinstance(extra, dict):
            cleaned += int(extra.get("cleaned") or 0)
    except Exception:
        pass
    return {"success": True, "cleaned": cleaned, "errors": errors[:5]}


def run_security_sweep(
    *,
    drift_limit: int = 100,
    jobs: Optional[List[str]] = None,
    preset: Optional[str] = None,
) -> Dict[str, Any]:
    """Run security sweep checks; safe to call from cron or HTTP."""
    if preset:
        jobs = list(PRESETS.get(str(preset).strip().lower()) or PRESETS["sweep"])
    if not jobs:
        jobs = list(PRESETS["sweep"])

    results: Dict[str, Any] = {}
    for job in jobs:
        try:
            if job == "conservation":
                from backend.services.mn2_conservation_gate import conservation_gate
                results[job] = conservation_gate()
            elif job == "points_drift":
                from backend.services.points_drift_service import scan_all
                results[job] = scan_all(limit=max(1, min(int(drift_limit or 100), 500)))
            elif job == "deposit_scanner":
                from backend.services.mn2_deposit_scanner import run_scanner
                results[job] = run_scanner()
            elif job == "treasury_reconcile":
                from backend.services.agent_admin_service import reconcile_treasury_pool
                results[job] = reconcile_treasury_pool()
            elif job == "withdrawal_risk":
                results[job] = check_withdrawal_risk()
            elif job == "anomaly":
                results[job] = check_anomaly()
            elif job == "session_cleanup":
                results[job] = check_session_cleanup()
            elif job == "backup":
                from backend.services.backup_service import run_backup
                results[job] = run_backup()
            elif job == "agent_kill_switch":
                from backend.services.agent_kill_switch import get_status
                results[job] = get_status()
            elif job == "customer_avatar_backfill":
                from backend.services.customer_avatar_service import backfill_missing_avatars
                results[job] = backfill_missing_avatars(limit=25)
            else:
                results[job] = {"error": f"unknown_job:{job}"}
        except Exception as exc:
            results[job] = {"error": str(exc)[:500]}

    ok = True
    for key, val in results.items():
        if not isinstance(val, dict):
            continue
        if val.get("error") and key in ("conservation", "points_drift"):
            ok = False
        if key == "conservation" and val.get("ok") is False:
            ok = False
        if key == "treasury_reconcile" and val.get("ok") is False:
            ok = False

    out = {
        "success": True,
        "ok": ok,
        "preset": preset,
        "jobs": jobs,
        "results": results,
    }
    try:
        from backend.services.activity_events_service import emit
        emit("security_cron_sweep", channel="ops", payload={"ok": ok, "jobs": jobs})
        if not ok:
            from backend.services.platform_news_publish import publish
            publish(
                item_id=f"security-sweep-{datetime.now(timezone.utc).strftime('%Y%m%d%H')}",
                title="Security sweep reported issues",
                summary="Ops: conservation/treasury reconcile flagged during security cron.",
                channel="ops",
                href="/dashboard",
                featured=False,
                channels=["ops", "discord"],
            )
    except Exception:
        pass
    return out
