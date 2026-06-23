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


def read_json_entries(path: str) -> List[Dict[str, Any]]:
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("entries"), list):
            return [x for x in data["entries"] if isinstance(x, dict)]
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except Exception:
        return []
    return []


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
) -> Tuple[float, Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float]]:
    total = 0.0
    by_user: Dict[str, float] = defaultdict(float)
    by_org: Dict[str, float] = defaultdict(float)
    by_provider: Dict[str, float] = defaultdict(float)
    by_item: Dict[str, float] = defaultdict(float)
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
        provider = str(r.get("provider") or "_unknown").strip().lower() or "_unknown"
        by_provider[provider] += amt
        item_id = str(r.get("item_id") or "_unknown").strip() or "_unknown"
        by_item[item_id] += amt
        org = (r.get("org_label") or "").strip()
        if org:
            by_org[org] += amt
    return total, dict(by_user), dict(by_org), dict(by_provider), dict(by_item)


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


def _sku_line_maps() -> Dict[str, str]:
    try:
        from backend.services.monetization_config_service import (
            get_coin_packs,
            get_content_bundles,
            get_digital_goods,
            list_subscription_plan_ids,
        )
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for p in get_coin_packs() or []:
        if p.get("id"):
            out[str(p["id"])] = "coin_pack"
    for g in get_digital_goods() or []:
        if g.get("id"):
            out[str(g["id"])] = "digital_good"
    for b in get_content_bundles() or []:
        if b.get("id"):
            out[str(b["id"])] = "bundle"
    for pid in list_subscription_plan_ids() or []:
        out[str(pid)] = "subscription"
    return out


def _line_for_ledger_row(row: Dict[str, Any], sku_lines: Dict[str, str]) -> str:
    provider = str(row.get("provider") or "").lower()
    if provider == "b2b_scr" or row.get("studio_sku_id") or row.get("deal_kind"):
        return "b2b_studio"
    item_id = str(row.get("item_id") or "").strip()
    if item_id in sku_lines:
        return sku_lines[item_id]
    if str(row.get("subscription_id") or "").strip():
        return "subscription"
    return "other"


def ledger_revenue_by_line(rows: List[Dict[str, Any]], *, since: Optional[datetime], scr_only: bool) -> Dict[str, float]:
    sku_lines = _sku_line_maps()
    out: Dict[str, float] = defaultdict(float)
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
        out[_line_for_ledger_row(r, sku_lines)] += amt
    return dict(out)


def mn2_shop_payments(
    rows: List[Dict[str, Any]],
    *,
    since: Optional[datetime],
    mn2_usd_price: Optional[float],
) -> Dict[str, Any]:
    total_mn2 = 0.0
    by_user: Dict[str, float] = defaultdict(float)
    by_item: Dict[str, float] = defaultdict(float)
    count = 0
    for r in rows:
        if (r.get("type") or "").strip() != "shop_payment":
            continue
        if not _in_time_window(r.get("created_at"), since):
            continue
        try:
            amt = abs(float(r.get("amount") or 0))
        except (TypeError, ValueError):
            continue
        if amt <= 0:
            continue
        count += 1
        total_mn2 += amt
        uid = str(r.get("user_id") or "_unknown").strip() or "_unknown"
        by_user[uid] += amt
        metadata = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
        item_id = str(metadata.get("item_id") or "_unknown").strip() or "_unknown"
        by_item[item_id] += amt
    estimated_usd = None
    if mn2_usd_price is not None and mn2_usd_price > 0:
        estimated_usd = total_mn2 * mn2_usd_price
    return {
        "count": count,
        "mn2_total": round(total_mn2, 8),
        "usd_estimated": round(estimated_usd, 6) if estimated_usd is not None else None,
        "mn2_usd_price": mn2_usd_price,
        "by_user_top": dict(sorted(by_user.items(), key=lambda x: -x[1])[:20]),
        "by_item": dict(sorted(by_item.items(), key=lambda x: -x[1])[:50]),
    }


def _mn2_ledger_path_default() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "mn2_ledger.json",
    )


def _mn2_usd_price_from_env() -> Optional[float]:
    raw = (os.environ.get("MN2_USD_PRICE") or os.environ.get("MN2_USD_PRICE_USD") or "").strip()
    if not raw:
        return None
    try:
        price = float(raw)
        return price if price > 0 else None
    except (TypeError, ValueError):
        return None


def run_ledger_metering_blend(
    *,
    ledger_path: Optional[str],
    metering_path: Optional[str],
    mn2_ledger_path: Optional[str] = None,
    mn2_usd_price: Optional[float] = None,
    since_days: Optional[float],
    scr_only: bool,
) -> Dict[str, Any]:
    from backend.services.cogs_metering_service import metering_jsonl_path
    from backend.services.monetization_ledger_service import payment_ledger_file_path

    lp = ledger_path or payment_ledger_file_path()
    mp = metering_path or metering_jsonl_path()
    mlp = mn2_ledger_path or _mn2_ledger_path_default()
    since = cutoff_datetime(since_days)
    mn2_price = mn2_usd_price if mn2_usd_price is not None else _mn2_usd_price_from_env()

    ledger_rows = read_jsonl(lp)
    meter_rows = read_jsonl(mp)
    mn2_rows = read_json_entries(mlp)

    rev_total, rev_user, rev_org, rev_provider, rev_item = ledger_revenue(ledger_rows, since=since, scr_only=scr_only)
    rev_line = ledger_revenue_by_line(ledger_rows, since=since, scr_only=scr_only)
    cogs_total, cogs_user, cogs_org = metering_cogs(meter_rows, since=since)
    mn2_shop = mn2_shop_payments(mn2_rows, since=since, mn2_usd_price=mn2_price)

    margin: Optional[float] = None
    if rev_total > 0:
        margin = (rev_total - cogs_total) / rev_total
    mn2_estimated_revenue = float(mn2_shop.get("usd_estimated") or 0)
    margin_with_mn2: Optional[float] = None
    if rev_total + mn2_estimated_revenue > 0:
        margin_with_mn2 = (rev_total + mn2_estimated_revenue - cogs_total) / (rev_total + mn2_estimated_revenue)

    users_both = set(rev_user.keys()) & set(cogs_user.keys())

    return {
        "success": True,
        "ledger_path": lp,
        "metering_path": mp,
        "mn2_ledger_path": mlp,
        "since_days": since_days,
        "since_cutoff_iso": since.isoformat() if since else None,
        "scr_only": scr_only,
        "ledger_rows_read": len(ledger_rows),
        "metering_rows_read": len(meter_rows),
        "mn2_ledger_rows_read": len(mn2_rows),
        "revenue_usd_total": round(rev_total, 6),
        "cogs_usd_total": round(cogs_total, 6),
        "blended_gross_margin_vs_metering": round(margin, 6) if margin is not None else None,
        "blended_gross_margin_with_mn2_estimate": round(margin_with_mn2, 6) if margin_with_mn2 is not None and mn2_estimated_revenue > 0 else None,
        "note": "Blended margin attributes all metering COGS in window to all ledger revenue — use for sanity checks only until job-level attribution exists.",
        "revenue_by_provider": dict(sorted(rev_provider.items(), key=lambda x: -x[1])),
        "revenue_by_line": dict(sorted(rev_line.items(), key=lambda x: -x[1])),
        "revenue_by_item_top": dict(sorted(rev_item.items(), key=lambda x: -x[1])[:50]),
        "mn2_shop_payments": mn2_shop,
        "revenue_by_user_top": dict(sorted(rev_user.items(), key=lambda x: -x[1])[:20]),
        "cogs_by_user_top": dict(sorted(cogs_user.items(), key=lambda x: -x[1])[:20]),
        "user_ids_with_both_ledger_and_metering": sorted(users_both)[:100],
        "revenue_by_org_label": rev_org,
        "cogs_by_org_label": cogs_org,
    }
