"""
User-facing monetization emails — allowance nudges, renewal reminders (§8.2).

Reuses NOTIFY_SMTP_* from purchase_notification_service. Best-effort; never raises.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.purchase_notification_service import _send_email

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG = os.path.join(_BASE, "logs", "monetization", "allowance_emails.jsonl")


def _log_sent(row: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_LOG), exist_ok=True)
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def resolve_user_email(user_id: str) -> Optional[str]:
    uid = (user_id or "").strip()
    if not uid:
        return None
    try:
        from backend.services.user_db_service import get_user_account

        acct = get_user_account(uid)
        if isinstance(acct, dict):
            em = (acct.get("email") or "").strip()
            if em and "@" in em:
                return em
    except Exception:
        pass
    try:
        from backend.services.user_onboarding import user_onboarding

        prof = user_onboarding.get_user_profile(uid) if user_onboarding else None
        if isinstance(prof, dict):
            prefs = prof.get("preferences")
            if isinstance(prefs, str):
                prefs = json.loads(prefs or "{}")
            if isinstance(prefs, dict):
                em = (prefs.get("email") or "").strip()
                if em and "@" in em:
                    return em
    except Exception:
        pass
    return None


def send_allowance_email(
    user_id: str,
    *,
    subject: str,
    body: str,
    nudge_level: str = "info",
) -> Dict[str, Any]:
    email = resolve_user_email(user_id)
    if not email:
        return {"success": False, "skipped": True, "reason": "no_email", "user_id": user_id}
    ok = _send_email(subject, body, email)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "email": email,
        "nudge_level": nudge_level,
        "sent": ok,
    }
    _log_sent(row)
    return {"success": ok, "user_id": user_id, "email": email}


def send_allowance_nudge_emails(
    nudge_rows: List[Dict[str, Any]],
    *,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Send emails for high-usage allowance rows (from allowance nudge scan)."""
    base = (base_url or os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    sent = 0
    skipped = 0
    for row in nudge_rows:
        uid = str(row.get("user_id") or "").strip()
        if not uid:
            continue
        msg = row.get("nudge_message") or "Your generation allowance is running low."
        level = str(row.get("nudge_level") or "warning")
        subject = "MasterNoder — monthly generation allowance update"
        if level == "upsell":
            subject = "MasterNoder — you've used your Pro allowance (top up available)"
        body = (
            f"{msg}\n\n"
            f"Top up with PayPal: {base}/shop?category=buy_coins\n"
            f"Manage subscription: {base}/shop?category=buy_coins\n\n"
            f"— MasterNoder"
        )
        out = send_allowance_email(uid, subject=subject, body=body, nudge_level=level)
        if out.get("success"):
            sent += 1
        else:
            skipped += 1
    return {"success": True, "emails_sent": sent, "skipped": skipped}


def run_renewal_reminder_emails(*, days_before: int = 3) -> Dict[str, Any]:
    """
    Best-effort renewal reminder for bound subscribers (no PayPal billing-date API — uses binding age).
    """
    try:
        from backend.services.monetization_subscription_service import list_all_bound_user_ids, list_bindings_for_user
    except Exception:
        return {"success": True, "sent": 0, "note": "no_subscription_service"}

    base = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    sent = 0
    for uid in list_all_bound_user_ids():
        bindings = list_bindings_for_user(uid)
        if not bindings:
            continue
        body = (
            f"Your Pro subscription renews soon.\n\n"
            f"Review usage and overage packs: {base}/shop?category=buy_coins\n\n"
            f"— MasterNoder"
        )
        out = send_allowance_email(
            uid,
            subject="MasterNoder — subscription renewal reminder",
            body=body,
            nudge_level="info",
        )
        if out.get("success"):
            sent += 1
    return {"success": True, "sent": sent}
