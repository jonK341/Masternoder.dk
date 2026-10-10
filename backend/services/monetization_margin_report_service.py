"""Tier C8 — weekly Phase C margin report (ledger vs metering via scr_blend)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.services.monetization_scr_blend_service import (
    cutoff_datetime,
    run_ledger_metering_blend,
)

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REPORT_LOG = os.path.join(_BASE, "logs", "monetization", "margin_report.jsonl")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_margin_report(*, since_days: float = 7) -> Dict[str, Any]:
    """Full + SCR-only blended margin for the rolling window."""
    since = cutoff_datetime(since_days)
    now = datetime.now(timezone.utc)
    period_end = now.strftime("%Y-%m-%d")
    period_start = since.strftime("%Y-%m-%d") if since else "all-time"

    blend = run_ledger_metering_blend(
        ledger_path=None,
        metering_path=None,
        mn2_ledger_path=None,
        mn2_usd_price=None,
        since_days=since_days,
        scr_only=False,
    )
    scr = run_ledger_metering_blend(
        ledger_path=None,
        metering_path=None,
        mn2_ledger_path=None,
        mn2_usd_price=None,
        since_days=since_days,
        scr_only=True,
    )

    rev = float(blend.get("revenue_usd_total") or 0)
    cogs = float(blend.get("cogs_usd_total") or 0)
    margin = blend.get("blended_gross_margin_vs_metering")
    margin_mn2 = blend.get("blended_gross_margin_with_mn2_estimate")
    mn2_shop = blend.get("mn2_shop_payments") if isinstance(blend.get("mn2_shop_payments"), dict) else {}

    return {
        "success": True,
        "generated_at": _iso_now(),
        "since_days": since_days,
        "period_label": f"{period_start} — {period_end}",
        "since_cutoff_iso": since.isoformat() if since else None,
        "revenue_usd_total": round(rev, 2),
        "cogs_usd_total": round(cogs, 2),
        "gross_profit_usd": round(rev - cogs, 2),
        "blended_gross_margin": margin,
        "blended_gross_margin_with_mn2": margin_mn2,
        "revenue_by_line": blend.get("revenue_by_line") or {},
        "revenue_by_provider": blend.get("revenue_by_provider") or {},
        "revenue_by_item_top": blend.get("revenue_by_item_top") or {},
        "mn2_shop_payments": mn2_shop,
        "scr_studio": {
            "revenue_usd_total": round(float(scr.get("revenue_usd_total") or 0), 2),
            "revenue_by_provider": scr.get("revenue_by_provider") or {},
            "revenue_by_item_top": scr.get("revenue_by_item_top") or {},
        },
        "cogs_by_user_top": blend.get("cogs_by_user_top") or {},
        "revenue_by_user_top": blend.get("revenue_by_user_top") or {},
        "user_ids_with_both_ledger_and_metering": blend.get("user_ids_with_both_ledger_and_metering") or [],
        "ledger_rows_read": blend.get("ledger_rows_read"),
        "metering_rows_read": blend.get("metering_rows_read"),
        "note": blend.get("note"),
    }


def format_margin_report_email(report: Dict[str, Any]) -> str:
    def _pct(v: Optional[float]) -> str:
        if v is None:
            return "n/a"
        return f"{float(v) * 100:.1f}%"

    lines = [
        f"Weekly Phase C margin report — {report.get('period_label', '')}",
        f"Generated: {report.get('generated_at', '')}",
        "",
        "=== Blended margin (payment_ledger vs metering) ===",
        f"Revenue USD: ${report.get('revenue_usd_total', 0):.2f}",
        f"COGS USD (metering): ${report.get('cogs_usd_total', 0):.2f}",
        f"Gross profit USD: ${report.get('gross_profit_usd', 0):.2f}",
        f"Blended gross margin: {_pct(report.get('blended_gross_margin'))}",
    ]
    margin_mn2 = report.get("blended_gross_margin_with_mn2")
    if margin_mn2 is not None:
        lines.append(f"Margin incl. MN2 shop est.: {_pct(margin_mn2)}")

    mn2 = report.get("mn2_shop_payments") or {}
    if mn2.get("count"):
        lines.extend([
            "",
            "=== MN2 shop payments (in-wallet) ===",
            f"Count: {mn2.get('count', 0)} · MN2: {mn2.get('mn2_total', 0)}",
        ])
        if mn2.get("usd_estimated") is not None:
            lines.append(f"USD estimated (MN2_USD_PRICE): ${float(mn2['usd_estimated']):.2f}")

    by_line = report.get("revenue_by_line") or {}
    if by_line:
        lines.extend(["", "=== Revenue by product line ==="])
        for name, amt in sorted(by_line.items(), key=lambda x: -float(x[1]))[:12]:
            lines.append(f"  · {name}: ${float(amt):.2f}")

    by_provider = report.get("revenue_by_provider") or {}
    if by_provider:
        lines.extend(["", "=== Revenue by provider ==="])
        for name, amt in sorted(by_provider.items(), key=lambda x: -float(x[1]))[:8]:
            lines.append(f"  · {name}: ${float(amt):.2f}")

    scr = report.get("scr_studio") or {}
    scr_rev = float(scr.get("revenue_usd_total") or 0)
    if scr_rev > 0:
        lines.extend([
            "",
            "=== B2B studio (SCR-only ledger) ===",
            f"SCR revenue USD: ${scr_rev:.2f}",
        ])
        for name, amt in list((scr.get("revenue_by_item_top") or {}).items())[:5]:
            lines.append(f"  · {name}: ${float(amt):.2f}")

    both = report.get("user_ids_with_both_ledger_and_metering") or []
    if both:
        lines.extend([
            "",
            f"Users with both ledger + metering in window: {len(both)}",
            f"  · sample: {', '.join(both[:8])}",
        ])

    base = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    lines.extend([
        "",
        f"Full JSON: {base}/api/monetization/report?since_days=7",
        f"SCR-only: {base}/api/monetization/report?since_days=7&scr_only=1",
        "",
        report.get("note") or "",
        "— MasterNoder ops",
    ])
    return "\n".join(lines)


def _append_report_log(row: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_REPORT_LOG), exist_ok=True)
        with open(_REPORT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def run_weekly_margin_report(*, since_days: float = 7, dry_run: bool = False) -> Dict[str, Any]:
    """Build margin report, email NOTIFY_ADMIN_EMAIL, append logs/monetization/margin_report.jsonl."""
    report = build_margin_report(since_days=since_days)
    out: Dict[str, Any] = {
        "success": True,
        "dry_run": dry_run,
        "period_label": report.get("period_label"),
        "revenue_usd_total": report.get("revenue_usd_total"),
        "cogs_usd_total": report.get("cogs_usd_total"),
        "blended_gross_margin": report.get("blended_gross_margin"),
    }

    if dry_run:
        out["report"] = report
        return out

    from backend.services.purchase_notification_service import NOTIFY_ADMIN_EMAIL, _send_email

    admin = (NOTIFY_ADMIN_EMAIL or "").strip()
    if not admin:
        out.update({"email_sent": False, "reason": "no_notify_admin_email"})
        _append_report_log({**out, "ts": _iso_now(), "report_summary": report})
        return out

    subject = f"MasterNoder weekly margin report ({report.get('period_label', '')})"
    body = format_margin_report_email(report)
    sent = _send_email(subject, body, admin)
    out["email_sent"] = sent
    out["admin_email"] = admin
    if not sent:
        out["reason"] = "smtp_failed_or_unconfigured"

    _append_report_log({
        "ts": _iso_now(),
        "email_sent": sent,
        "admin_email": admin,
        "period_label": report.get("period_label"),
        "summary": {
            "revenue_usd": out.get("revenue_usd_total"),
            "cogs_usd": out.get("cogs_usd_total"),
            "margin": out.get("blended_gross_margin"),
        },
    })
    return out
