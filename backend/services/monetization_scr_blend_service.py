"""
Blended revenue (payment_ledger.jsonl) vs COGS (metering.jsonl) — sanity checks for phase C margin.

Job-level attribution is future work; this aggregates by optional time window and user/org.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


def parse_iso_ts(s: Any) -> Optional[datetime]:
    if not s:
        return None
    try:
        raw = str(s).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def read_jsonl(path: str, max_lines: int = 500_000) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path or not os.path.isfile(path):
        return out
    n = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if n >= max_lines:
                break
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            n += 1
    return out


def cutoff_datetime(since_days: Optional[float]) -> Optional[datetime]:
    if since_days is None or since_days <= 0:
        return None
    return datetime.now(timezone.utc) - timedelta(days=float(since_days))


def _in_time_window(ts_raw: Any, since: Optional[datetime]) -> bool:
    """Include row if no filter, or ts exists and is >= since. Exclude if filter on and ts missing."""
    if since is None:
        return True
    ts = parse_iso_ts(ts_raw)
    if ts is None:
        return False
    return ts >= since


def ledger_revenue(
    rows: List[Dict[str, Any]],
    *,
    since: Optional[datetime],
    scr_only: bool,
) -> Tuple[float, Dict[str, float], Dict[str, float]]:
    total = 0.0
    by_user: Dict[str, float] = defaultdict(float)
    by_org: Dict[str, float] = defaultdict(float)
    for r in rows:
        if scr_only:
            prov = (r.get("provider") or "").strip().lower()
            if prov != "b2b_scr" and not (r.get("deal_kind") or r.get("studio_sku_id")):
                continue
        if not _in_time_window(r.get("ts"), since):
            continue
        amt = float(r.get("amount_usd") or 0)
        if amt <= 0:
            continue
        total += amt
        uid = str(r.get("user_id") or "").strip() or "_unknown"
        by_user[uid] += amt
        org = (r.get("org_label") or "").strip()
        if org:
            by_org[org] += amt
    return total, dict(by_user), dict(by_org)


def metering_cogs(
    rows: List[Dict[str, Any]],
    *,
    since: Optional[datetime],
) -> Tuple[float, Dict[str, float], Dict[str, float]]:
    total = 0.0
    by_user: Dict[str, float] = defaultdict(float)
    by_org: Dict[str, float] = defaultdict(float)
    for r in rows:
        if not _in_time_window(r.get("ts"), since):
            continue
        cogs = r.get("cogs_usd") or {}
        t = float(cogs.get("total_usd") or 0)
        if t <= 0:
            continue
        total += t
        uid = str(r.get("user_id") or "").strip() or "_unknown"
        by_user[uid] += t
        org = (r.get("org_label") or "").strip()
        if org:
            by_org[org] += t
    return total, dict(by_user), dict(by_org)


def run_ledger_metering_blend(
    *,
    ledger_path: Optional[str],
    metering_path: Optional[str],
    since_days: Optional[float],
    scr_only: bool,
) -> Dict[str, Any]:
    from backend.services.cogs_metering_service import metering_jsonl_path
    from backend.services.monetization_ledger_service import payment_ledger_file_path

    lp = ledger_path or payment_ledger_file_path()
    mp = metering_path or metering_jsonl_path()
    since = cutoff_datetime(since_days)

    ledger_rows = read_jsonl(lp)
    meter_rows = read_jsonl(mp)

    rev_total, rev_user, rev_org = ledger_revenue(ledger_rows, since=since, scr_only=scr_only)
    cogs_total, cogs_user, cogs_org = metering_cogs(meter_rows, since=since)

    margin: Optional[float] = None
    if rev_total > 0:
        margin = (rev_total - cogs_total) / rev_total

    users_both = set(rev_user.keys()) & set(cogs_user.keys())

    return {
        "success": True,
        "ledger_path": lp,
        "metering_path": mp,
        "since_days": since_days,
        "since_cutoff_iso": since.isoformat() if since else None,
        "scr_only": scr_only,
        "ledger_rows_read": len(ledger_rows),
        "metering_rows_read": len(meter_rows),
        "revenue_usd_total": round(rev_total, 6),
        "cogs_usd_total": round(cogs_total, 6),
        "blended_gross_margin_vs_metering": round(margin, 6) if margin is not None else None,
        "note": "Blended margin attributes all metering COGS in window to all ledger revenue — use for sanity checks only until job-level attribution exists.",
        "revenue_by_user_top": dict(sorted(rev_user.items(), key=lambda x: -x[1])[:20]),
        "cogs_by_user_top": dict(sorted(cogs_user.items(), key=lambda x: -x[1])[:20]),
        "user_ids_with_both_ledger_and_metering": sorted(users_both)[:100],
        "revenue_by_org_label": rev_org,
        "cogs_by_org_label": cogs_org,
    }
