"""
Usage vs allowance for PayPal subscriptions and prepaid credits (§8.2 habit loops).

Aggregates metering.jsonl burn for a user in a billing window and compares to
subscription monthly_generation_credits or wallet balance. Powers in-app nudges and
optional cron logging — not full email automation yet.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services.monetization_config_service import (
    get_credit_reference_fraction,
    credits_to_ref_eq_generations,
    get_subscription_plan,
    ratio_to_credits_used,
    ref_eq_label,
)


def _parse_ts(s: Any) -> Optional[datetime]:
    if not s:
        return None
    try:
        raw = str(s).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def _metering_path() -> str:
    from backend.services.cogs_metering_service import metering_jsonl_path

    return metering_jsonl_path()


def _user_metering_usage(
    user_id: str,
    *,
    since: Optional[datetime],
    max_lines: int = 100_000,
) -> Tuple[float, float, int]:
    """
    Returns (credits_used, ref_eq_generations_used, job_count) for rich_video rows.
    """
    uid = (user_id or "").strip()
    if not uid:
        return 0.0, 0.0, 0
    path = _metering_path()
    if not os.path.isfile(path):
        return 0.0, 0.0, 0

    credits_used = 0.0
    ref_eq = 0.0
    jobs = 0
    frac = get_credit_reference_fraction()
    n = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if n >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                n += 1
                if str(row.get("user_id") or "").strip() != uid:
                    continue
                ts = _parse_ts(row.get("ts"))
                if since and (ts is None or ts < since):
                    continue
                ratio_raw = row.get("ratio_vs_reference_job")
                if ratio_raw is None:
                    continue
                try:
                    ratio = float(ratio_raw)
                except (TypeError, ValueError):
                    continue
                jobs += 1
                ref_eq += ratio
                credits_used += ratio_to_credits_used(ratio)
    except Exception:
        pass

    return round(credits_used, 4), round(ref_eq, 4), jobs


def _wallet_generation_credits(user_id: str) -> float:
    try:
        from backend.services.unified_points_database import unified_points_db

        pts = unified_points_db.get_all_points(str(user_id))
        p = pts.get("points") if isinstance(pts.get("points"), dict) else {}
        systems = pts.get("systems") if isinstance(pts.get("systems"), dict) else {}
        for key in ("generation_credits", "video_credits"):
            v = p.get(key)
            if v is None:
                v = systems.get(key)
            if v is not None:
                return round(float(v), 4)
        coins = p.get("coins")
        if coins is None:
            coins = systems.get("coins")
        if coins is not None and float(coins) > 0:
            return round(float(coins) / 400.0, 4)
    except Exception:
        pass
    return 0.0


def _user_subscription_context(user_id: str) -> Dict[str, Any]:
    try:
        from backend.services.monetization_subscription_service import list_bindings_for_user

        bindings = list_bindings_for_user(user_id)
    except Exception:
        bindings = []
    if not bindings:
        return {"has_subscription": False}
    b = bindings[0]
    plan_id = str(b.get("plan_id") or "").strip()
    pinfo = get_subscription_plan(plan_id) if plan_id else {}
    try:
        monthly = float(pinfo.get("monthly_generation_credits") or 0)
    except (TypeError, ValueError):
        monthly = 0.0
    return {
        "has_subscription": True,
        "subscription_id": b.get("subscription_id"),
        "plan_id": plan_id,
        "plan_label": pinfo.get("label") or plan_id,
        "tier": pinfo.get("tier"),
        "monthly_generation_credits": monthly,
        "monthly_ref_eq_generations": credits_to_ref_eq_generations(monthly),
        "monthly_ref_eq_label": ref_eq_label(monthly) or None,
    }


def _nudge_from_usage(
    *,
    credits_used: float,
    monthly_allowance: float,
    wallet_credits: float,
    has_subscription: bool,
) -> Dict[str, Any]:
    if has_subscription and monthly_allowance > 0:
        pct = min(999.0, round(100.0 * credits_used / monthly_allowance, 1))
        remaining = max(0.0, round(monthly_allowance - credits_used, 2))
        level = "none"
        message = None
        if pct >= 100:
            level = "upsell"
            message = (
                f"You've used about {pct:g}% of your monthly allowance "
                f"({credits_used:g} of {monthly_allowance:g} generation credits). "
                "Consider a coin pack for overage or wait for your next billing cycle."
            )
        elif pct >= 80:
            level = "warning"
            message = (
                f"You've used about {pct:g}% of your monthly allowance "
                f"({remaining:g} generation credits left this period)."
            )
        elif pct >= 50:
            level = "info"
            message = (
                f"You've used about {pct:g}% of your monthly allowance "
                f"({remaining:g} generation credits remaining)."
            )
        return {
            "nudge_level": level,
            "nudge_message": message,
            "percent_of_monthly_allowance": pct,
            "credits_remaining_in_allowance": remaining,
        }

    if wallet_credits > 0:
        return {
            "nudge_level": "info",
            "nudge_message": f"You have {wallet_credits:g} generation credits in your wallet.",
            "percent_of_monthly_allowance": None,
            "credits_remaining_in_allowance": wallet_credits,
        }
    return {
        "nudge_level": "none",
        "nudge_message": None,
        "percent_of_monthly_allowance": None,
        "credits_remaining_in_allowance": 0.0,
    }


def get_user_usage_allowance(
    user_id: str,
    *,
    period_days: int = 30,
) -> Dict[str, Any]:
    """
    Usage vs allowance for profile/shop nudges.

    period_days: rolling window for metering burn (default 30, aligned to subscription month).
    """
    uid = (user_id or "").strip()
    if not uid or uid.lower() == "default_user":
        return {"success": False, "error": "user_id_required"}

    since = datetime.now(timezone.utc) - timedelta(days=max(1, int(period_days)))
    credits_used, ref_eq_used, job_count = _user_metering_usage(uid, since=since)
    wallet = _wallet_generation_credits(uid)
    sub = _user_subscription_context(uid)
    monthly = float(sub.get("monthly_generation_credits") or 0) if sub.get("has_subscription") else 0.0
    nudge = _nudge_from_usage(
        credits_used=credits_used,
        monthly_allowance=monthly,
        wallet_credits=wallet,
        has_subscription=bool(sub.get("has_subscription")),
    )

    return {
        "success": True,
        "user_id": uid,
        "period_days": period_days,
        "period_start_iso": since.isoformat(),
        "metering": {
            "jobs_in_period": job_count,
            "generation_credits_used": credits_used,
            "reference_equivalent_generations_used": ref_eq_used,
        },
        "wallet_generation_credits": wallet,
        "subscription": sub,
        "nudge": nudge,
        "credit_definition": {
            "reference_fraction_per_credit": get_credit_reference_fraction(),
        },
    }


def run_allowance_nudge_scan(
    *,
    min_percent: float = 75.0,
    period_days: int = 30,
) -> Dict[str, Any]:
    """
    Cron helper: scan subscribed users and append nudge rows when usage is high.
    Writes logs/monetization/allowance_nudges.jsonl (best-effort).
    """
    try:
        from backend.services.monetization_subscription_service import list_all_bound_user_ids
    except Exception:
        return {"success": True, "scanned": 0, "nudged": 0, "note": "no_bindings"}

    user_ids = list_all_bound_user_ids()
    nudged: List[Dict[str, Any]] = []
    for uid in user_ids:
        summary = get_user_usage_allowance(uid, period_days=period_days)
        if not summary.get("success"):
            continue
        nudge = summary.get("nudge") or {}
        pct = nudge.get("percent_of_monthly_allowance")
        level = nudge.get("nudge_level")
        if level in ("warning", "upsell") or (pct is not None and float(pct) >= min_percent):
            row = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "user_id": uid,
                "nudge_level": level,
                "percent_of_monthly_allowance": pct,
                "nudge_message": nudge.get("nudge_message"),
                "subscription": summary.get("subscription"),
                "metering": summary.get("metering"),
            }
            nudged.append(row)

    log_path = None
    if nudged:
        base = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "logs",
        )
        log_path = os.path.join(base, "monetization", "allowance_nudges.jsonl")
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                for row in nudged:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            log_path = None

    return {
        "success": True,
        "scanned": len(user_ids),
        "nudged": len(nudged),
        "log_path": log_path,
        "samples": nudged[:5],
        "emails": _send_nudge_emails(nudged),
    }


def _send_nudge_emails(nudged: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not nudged:
        return {"sent": 0, "skipped": 0}
    try:
        from backend.services.monetization_email_service import send_allowance_nudge_emails

        return send_allowance_nudge_emails(nudged)
    except Exception:
        return {"sent": 0, "skipped": len(nudged), "error": "email_service_failed"}
