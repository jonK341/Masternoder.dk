"""Tier C3 — weekly revenue pulse: payment_ledger + hosting + camgirls tips."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ORDERS_PATH = os.path.join(_BASE, "data", "mn2_masternode_orders.json")
_TIPS_PATH = os.path.join(_BASE, "data", "camgirls_tips.jsonl")
_PULSE_LOG = os.path.join(_BASE, "logs", "monetization", "revenue_pulse.jsonl")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _mn2_usd_price() -> Optional[float]:
    raw = (os.environ.get("MN2_USD_PRICE") or os.environ.get("MN2_USD_PRICE_USD") or "").strip()
    if not raw:
        return None
    try:
        p = float(raw)
        return p if p > 0 else None
    except (TypeError, ValueError):
        return None


def _hosting_pulse(since) -> Dict[str, Any]:
    from backend.services.monetization_scr_blend_service import parse_iso_ts, _in_time_window

    if not os.path.isfile(_ORDERS_PATH):
        return {"paid_orders": 0, "slots_sold": 0, "usd_total": 0.0, "by_payment_method": {}}

    try:
        with open(_ORDERS_PATH, "r", encoding="utf-8") as f:
            orders = json.load(f)
    except Exception:
        orders = {}

    paid_orders = 0
    slots = 0
    usd_total = 0.0
    by_method: Dict[str, float] = defaultdict(float)

    for order in (orders.values() if isinstance(orders, dict) else []):
        if not isinstance(order, dict) or order.get("status") != "paid":
            continue
        ts = order.get("paid_at") or order.get("updated_at") or order.get("created_at")
        if not _in_time_window(ts, since):
            continue
        paid_orders += 1
        slot_n = int(order.get("slots") or 0)
        slots += slot_n
        usd = float(order.get("usd_total") or 0)
        if usd <= 0:
            usd = float(order.get("usd_per_slot") or 0) * max(slot_n, 1)
        usd_total += usd
        method = str(order.get("payment_method") or "unknown").strip().lower() or "unknown"
        by_method[method] += usd

    return {
        "paid_orders": paid_orders,
        "slots_sold": slots,
        "usd_total": round(usd_total, 2),
        "by_payment_method": dict(sorted(by_method.items(), key=lambda x: -x[1])),
    }


def _camgirls_tips_pulse(since) -> Dict[str, Any]:
    from backend.services.monetization_scr_blend_service import read_jsonl, _in_time_window

    rows = read_jsonl(_TIPS_PATH)
    tip_count = 0
    mn2_total = 0.0
    fiat_count = 0
    by_performer: Dict[str, float] = defaultdict(float)

    for row in rows:
        if not _in_time_window(row.get("ts"), since):
            continue
        try:
            amt = float(row.get("amount_mn2") or 0)
        except (TypeError, ValueError):
            continue
        if amt <= 0:
            continue
        tip_count += 1
        mn2_total += amt
        pid = str(row.get("performer_id") or "_unknown").strip() or "_unknown"
        by_performer[pid] += amt
        if row.get("fiat_settled") or row.get("payment_provider") == "paypal":
            fiat_count += 1

    price = _mn2_usd_price()
    usd_est = round(mn2_total * price, 2) if price else None

    return {
        "tip_count": tip_count,
        "mn2_total": round(mn2_total, 8),
        "usd_estimated": usd_est,
        "fiat_settled_count": fiat_count,
        "by_performer_top": dict(sorted(by_performer.items(), key=lambda x: -x[1])[:10]),
    }


def build_revenue_pulse(*, since_days: float = 7) -> Dict[str, Any]:
    from backend.services.monetization_scr_blend_service import (
        _in_time_window,
        cutoff_datetime,
        ledger_revenue,
        ledger_revenue_by_line,
        metering_cogs,
        read_jsonl,
    )
    from backend.services.monetization_ledger_service import payment_ledger_file_path
    from backend.services.cogs_metering_service import metering_jsonl_path

    since = cutoff_datetime(since_days)
    ledger_rows = read_jsonl(payment_ledger_file_path())
    meter_rows = read_jsonl(metering_jsonl_path())

    rev_total, _, _, rev_provider, rev_item = ledger_revenue(
        ledger_rows, since=since, scr_only=False
    )
    rev_line = ledger_revenue_by_line(ledger_rows, since=since, scr_only=False)
    cogs_total, _, _ = metering_cogs(meter_rows, since=since)

    payment_count = 0
    camgirls_ledger_usd = 0.0
    for r in ledger_rows:
        if not _in_time_window(r.get("ts"), since):
            continue
        amt = float(r.get("amount_usd") or 0)
        if amt <= 0:
            continue
        payment_count += 1
        extra = r.get("extra") if isinstance(r.get("extra"), dict) else {}
        if extra.get("product") == "camgirls" or str(r.get("item_name") or "").startswith("camgirls_"):
            camgirls_ledger_usd += amt

    hosting = _hosting_pulse(since)
    tips = _camgirls_tips_pulse(since)

    margin = None
    if rev_total > 0:
        margin = round((rev_total - cogs_total) / rev_total, 4)

    now = datetime.now(timezone.utc)
    period_end = now.strftime("%Y-%m-%d")
    period_start = since.strftime("%Y-%m-%d") if since else "all-time"

    return {
        "success": True,
        "generated_at": _iso_now(),
        "since_days": since_days,
        "period_label": f"{period_start} — {period_end}",
        "since_cutoff_iso": since.isoformat() if since else None,
        "ledger": {
            "revenue_usd_total": round(rev_total, 2),
            "payment_count": payment_count,
            "by_provider": dict(sorted(rev_provider.items(), key=lambda x: -x[1])),
            "by_line": dict(sorted(rev_line.items(), key=lambda x: -x[1])),
            "by_item_top": dict(sorted(rev_item.items(), key=lambda x: -x[1])[:15]),
            "camgirls_paypal_usd": round(camgirls_ledger_usd, 2),
        },
        "hosting": hosting,
        "camgirls_tips": tips,
        "cogs_usd_total": round(cogs_total, 2),
        "blended_gross_margin": margin,
    }


def format_revenue_pulse_email(report: Dict[str, Any]) -> str:
    ledger = report.get("ledger") or {}
    hosting = report.get("hosting") or {}
    tips = report.get("camgirls_tips") or {}
    lines = [
        f"Weekly revenue pulse — {report.get('period_label', '')}",
        f"Generated: {report.get('generated_at', '')}",
        "",
        "=== Payment ledger (USD) ===",
        f"Total: ${ledger.get('revenue_usd_total', 0):.2f} ({ledger.get('payment_count', 0)} captures)",
    ]
    for name, amt in (ledger.get("by_line") or {}).items():
        lines.append(f"  · {name}: ${amt:.2f}")
    for name, amt in list((ledger.get("by_provider") or {}).items())[:8]:
        lines.append(f"  · {name}: ${amt:.2f}")

    lines.extend([
        "",
        "=== Masternode hosting ===",
        f"Paid orders: {hosting.get('paid_orders', 0)} · slots: {hosting.get('slots_sold', 0)} · USD: ${hosting.get('usd_total', 0):.2f}",
    ])
    for method, amt in (hosting.get("by_payment_method") or {}).items():
        lines.append(f"  · {method}: ${amt:.2f}")

    lines.extend([
        "",
        "=== Camgirls tips ===",
        f"Tips: {tips.get('tip_count', 0)} · MN2: {tips.get('mn2_total', 0)}",
    ])
    if tips.get("usd_estimated") is not None:
        lines.append(f"  · USD est. (MN2_USD_PRICE): ${tips['usd_estimated']:.2f}")
    cam_usd = ledger.get("camgirls_paypal_usd")
    if cam_usd:
        lines.append(f"  · PayPal camgirls ledger: ${cam_usd:.2f}")

    margin = report.get("blended_gross_margin")
    cogs = report.get("cogs_usd_total")
    if margin is not None:
        lines.extend([
            "",
            "=== COGS sanity (metering) ===",
            f"COGS USD: ${cogs:.2f} · blended margin vs ledger: {margin * 100:.1f}%",
        ])

    base = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    lines.extend(["", f"Full report API: {base}/api/monetization/report?since_days=7", "— MasterNoder ops"])
    return "\n".join(lines)


def _append_pulse_log(row: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_PULSE_LOG), exist_ok=True)
        with open(_PULSE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def run_weekly_revenue_pulse(*, since_days: float = 7, dry_run: bool = False) -> Dict[str, Any]:
    """Build pulse, email NOTIFY_ADMIN_EMAIL, append logs/monetization/revenue_pulse.jsonl."""
    report = build_revenue_pulse(since_days=since_days)
    out: Dict[str, Any] = {
        "success": True,
        "dry_run": dry_run,
        "period_label": report.get("period_label"),
        "revenue_usd_total": (report.get("ledger") or {}).get("revenue_usd_total"),
        "hosting_usd_total": (report.get("hosting") or {}).get("usd_total"),
        "tip_count": (report.get("camgirls_tips") or {}).get("tip_count"),
    }

    if dry_run:
        out["report"] = report
        return out

    from backend.services.purchase_notification_service import NOTIFY_ADMIN_EMAIL, _send_email

    admin = (NOTIFY_ADMIN_EMAIL or "").strip()
    if not admin:
        out.update({"email_sent": False, "reason": "no_notify_admin_email"})
        _append_pulse_log({**out, "ts": _iso_now(), "report_summary": report})
        return out

    subject = f"MasterNoder weekly revenue pulse ({report.get('period_label', '')})"
    body = format_revenue_pulse_email(report)
    sent = _send_email(subject, body, admin)
    out["email_sent"] = sent
    out["admin_email"] = admin
    if not sent:
        out["reason"] = "smtp_failed_or_unconfigured"

    _append_pulse_log({
        "ts": _iso_now(),
        "email_sent": sent,
        "admin_email": admin,
        "period_label": report.get("period_label"),
        "summary": {
            "ledger_usd": out.get("revenue_usd_total"),
            "hosting_usd": out.get("hosting_usd_total"),
            "tips": out.get("tip_count"),
        },
    })
    return out
