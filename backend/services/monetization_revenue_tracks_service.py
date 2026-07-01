"""
Monetization machine — revenue tracks registry and per-track metrics.

Defines parallel revenue streams (Tiers A–D) and aggregates USD / counts from
payment ledger, hosting orders, camgirls tips, and ops signals.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TRACKS_PATH = os.path.join(_BASE, "data", "monetization_revenue_tracks.json")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tracks_path() -> str:
    override = (os.environ.get("MONETIZATION_REVENUE_TRACKS_PATH") or "").strip()
    return override or _TRACKS_PATH


@lru_cache(maxsize=1)
def _load_raw() -> Dict[str, Any]:
    path = _tracks_path()
    if not os.path.isfile(path):
        return {"tracks": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"tracks": []}
    except Exception:
        return {"tracks": []}


def reload_revenue_tracks() -> None:
    _load_raw.cache_clear()


def get_north_star() -> Dict[str, Any]:
    raw = _load_raw()
    ns = raw.get("north_star") if isinstance(raw.get("north_star"), dict) else {}
    return dict(ns)


def list_track_definitions() -> List[Dict[str, Any]]:
    raw = _load_raw()
    tracks = raw.get("tracks") or []
    return [dict(t) for t in tracks if isinstance(t, dict) and t.get("id")]


def _sku_line_maps() -> Dict[str, str]:
    try:
        from backend.services.monetization_scr_blend_service import _sku_line_maps as _maps
        return _maps()
    except Exception:
        return {}


def _line_for_row(row: Dict[str, Any], sku_lines: Dict[str, str]) -> str:
    from backend.services.monetization_scr_blend_service import _line_for_ledger_row
    return _line_for_ledger_row(row, sku_lines)


def _row_matches_track(row: Dict[str, Any], track: Dict[str, Any], sku_lines: Dict[str, str]) -> bool:
    """Match ledger row to track via ledger_lines and item_id patterns."""
    item_id = str(row.get("item_id") or "").strip().lower()
    item_name = str(row.get("item_name") or "").strip().lower()
    extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
    product = str(extra.get("product") or "").strip().lower()

    prefixes = [str(p).lower() for p in (track.get("item_id_contains") or [])]
    if prefixes:
        hay = f"{item_id} {item_name} {product}"
        if any(p in hay for p in prefixes):
            return True

    lines = [str(l).lower() for l in (track.get("ledger_lines") or [])]
    if lines:
        row_line = _line_for_row(row, sku_lines)
        if row_line in lines:
            if not prefixes:
                return True
            hay = f"{item_id} {item_name} {product}"
            return any(p in hay for p in prefixes)

    if track.get("metric_source") == "camgirls":
        if product == "camgirls" or item_name.startswith("camgirls_") or "camgirls" in item_id:
            return True

    return False


def _aggregate_ledger_for_tracks(
    tracks: List[Dict[str, Any]],
    *,
    since_days: Optional[float] = 7,
) -> Dict[str, Dict[str, Any]]:
    from backend.services.monetization_scr_blend_service import cutoff_datetime, read_jsonl, _in_time_window
    from backend.services.monetization_ledger_service import payment_ledger_file_path

    since = cutoff_datetime(since_days)
    rows = read_jsonl(payment_ledger_file_path())
    sku_lines = _sku_line_maps()

    out: Dict[str, Dict[str, Any]] = {
        t["id"]: {"revenue_usd": 0.0, "transaction_count": 0, "by_provider": defaultdict(float)}
        for t in tracks
        if t.get("metric_source") in ("ledger", "camgirls", None) or t.get("ledger_lines") or t.get("item_id_contains")
    }

    for row in rows:
        if not _in_time_window(row.get("ts"), since):
            continue
        amt = float(row.get("amount_usd") or 0)
        if amt <= 0:
            continue
        provider = str(row.get("provider") or "_unknown").strip().lower() or "_unknown"

        for track in tracks:
            tid = track.get("id")
            if tid not in out:
                continue
            if _row_matches_track(row, track, sku_lines):
                out[tid]["revenue_usd"] += amt
                out[tid]["transaction_count"] += 1
                out[tid]["by_provider"][provider] += amt
                break

    for tid, m in out.items():
        m["revenue_usd"] = round(m["revenue_usd"], 2)
        m["by_provider"] = dict(sorted(m["by_provider"].items(), key=lambda x: -x[1]))
    return out


def _hosting_metrics(*, since_days: Optional[float] = 7) -> Dict[str, Any]:
    from backend.services.monetization_revenue_pulse_service import _hosting_pulse
    from backend.services.monetization_scr_blend_service import cutoff_datetime

    since = cutoff_datetime(since_days)
    return _hosting_pulse(since)


def _camgirls_metrics(*, since_days: Optional[float] = 7) -> Dict[str, Any]:
    from backend.services.monetization_revenue_pulse_service import _camgirls_tips_pulse
    from backend.services.monetization_scr_blend_service import cutoff_datetime

    since = cutoff_datetime(since_days)
    tips = _camgirls_tips_pulse(since)
    usd = tips.get("usd_estimated")
    return {
        "revenue_usd": usd if usd is not None else 0.0,
        "transaction_count": tips.get("tip_count", 0),
        "mn2_total": tips.get("mn2_total", 0),
        "usd_estimated": usd,
    }


def _casino_metrics(*, since_days: Optional[float] = 7) -> Dict[str, Any]:
    from backend.services.monetization_revenue_pulse_service import _casino_pulse
    from backend.services.monetization_scr_blend_service import cutoff_datetime

    since = cutoff_datetime(since_days)
    pulse = _casino_pulse(since)
    usd = float(pulse.get("paypal_deposit_usd") or 0)
    return {
        "revenue_usd": usd,
        "transaction_count": int(pulse.get("paypal_deposit_count") or 0),
        "bet_count": int(pulse.get("bet_count") or 0),
        "wager_total": pulse.get("wager_total", 0),
        "house_net_est": pulse.get("house_net_est", 0),
    }


def _config_flag_enabled(flag: str) -> bool:
    raw = (os.environ.get(flag) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _ops_metrics_for_track(track: Dict[str, Any]) -> Dict[str, Any]:
    source = track.get("metric_source") or "ledger"
    tid = track.get("id", "")

    if source == "hosting" or tid in ("A3", "B2"):
        h = _hosting_metrics(since_days=7)
        return {
            "revenue_usd": h.get("usd_total", 0),
            "transaction_count": h.get("paid_orders", 0),
            "slots_sold": h.get("slots_sold", 0),
            "by_payment_method": h.get("by_payment_method", {}),
        }

    if source == "camgirls" or tid == "A5":
        return _camgirls_metrics(since_days=7)

    if source == "casino" or tid == "A9":
        return _casino_metrics(since_days=7)

    if source == "stream":
        return {"revenue_usd": None, "transaction_count": 0, "stream_id": track.get("stream_id"), "metric_source": "stream"}

    if source == "config":
        flag = track.get("config_flag") or "MONETIZATION_TIER_ENFORCEMENT"
        enabled = _config_flag_enabled(flag)
        return {
            "revenue_usd": None,
            "transaction_count": 0,
            "feature_enabled": enabled,
            "config_flag": flag,
        }

    if source == "pulse" or tid == "C3":
        return {"revenue_usd": None, "transaction_count": 0, "ops": "weekly_revenue_pulse"}

    if source == "margin_report" or tid == "C8":
        return {"revenue_usd": None, "transaction_count": 0, "ops": "margin_report_cron"}

    if source == "fee" or tid == "B5":
        return {
            "revenue_usd": None,
            "transaction_count": 0,
            "fee_percent": track.get("fee_percent", 5),
            "note": "Fee embedded in auction settlements — see ledger other line",
        }

    if source in ("promo", "referral", "upsell", "none", "cron", "escrow", "livekit"):
        return {"revenue_usd": None, "transaction_count": 0, "metric_source": source}

    return {}


def get_track_metrics(track_id: str, *, since_days: float = 7) -> Dict[str, Any]:
    tracks = list_track_definitions()
    track = next((t for t in tracks if t.get("id") == track_id), None)
    if not track:
        return {"success": False, "error": "track_not_found", "track_id": track_id}

    source = track.get("metric_source") or "ledger"
    metrics: Dict[str, Any] = {"since_days": since_days}

    if source == "hosting" or track_id in ("A3", "B2"):
        metrics.update(_hosting_metrics(since_days=since_days))
    elif source == "casino" or track_id == "A9":
        metrics.update(_casino_metrics(since_days=since_days))
    elif source == "camgirls":
        metrics.update(_camgirls_metrics(since_days=since_days))
    elif source == "stream":
        metrics.update(_ops_metrics_for_track(track))
        sid = track.get("stream_id")
        if sid:
            try:
                from backend.services.monetization_streams_service import list_distribution_streams

                match = next((s for s in list_distribution_streams() if s.get("id") == sid), None)
                if match:
                    from backend.services.monetization_streams_service import _stream_metrics
                    metrics.update(_stream_metrics(match))
            except Exception:
                pass
    elif source in ("ledger",) or track.get("ledger_lines") or track.get("item_id_contains"):
        agg = _aggregate_ledger_for_tracks([track], since_days=since_days)
        metrics.update(agg.get(track_id, {"revenue_usd": 0.0, "transaction_count": 0}))
    else:
        metrics.update(_ops_metrics_for_track(track))

    return {
        "success": True,
        "track_id": track_id,
        "track": {k: track.get(k) for k in ("id", "tier", "name", "status", "revenue_model", "metric_source")},
        "metrics": metrics,
        "generated_at": _iso_now(),
    }


def list_tracks(*, include_metrics: bool = False, since_days: float = 7) -> Dict[str, Any]:
    tracks = list_track_definitions()
    ledger_agg = _aggregate_ledger_for_tracks(tracks, since_days=since_days) if include_metrics else {}

    rows = []
    for track in tracks:
        entry = {
            "id": track.get("id"),
            "tier": track.get("tier"),
            "name": track.get("name"),
            "status": track.get("status"),
            "revenue_model": track.get("revenue_model"),
            "metric_source": track.get("metric_source"),
        }
        if include_metrics:
            tid = track.get("id", "")
            source = track.get("metric_source") or "ledger"
            if tid in ledger_agg and ledger_agg[tid].get("transaction_count", 0) > 0:
                entry["metrics"] = ledger_agg[tid]
            elif source in ("hosting", "casino") or tid in ("A3", "A9", "B2"):
                entry["metrics"] = _ops_metrics_for_track(track)
            elif source not in ("ledger", "camgirls"):
                entry["metrics"] = _ops_metrics_for_track(track)
            else:
                entry["metrics"] = ledger_agg.get(tid, {"revenue_usd": 0.0, "transaction_count": 0})
        rows.append(entry)

    return {
        "success": True,
        "north_star": get_north_star(),
        "count": len(rows),
        "tracks": rows,
        "generated_at": _iso_now(),
        "since_days": since_days if include_metrics else None,
    }


def get_machine_status(*, since_days: float = 7) -> Dict[str, Any]:
    """Overall monetization machine health — track counts, revenue rollup, tier breakdown."""
    tracks = list_track_definitions()
    by_tier: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "live": 0, "shipped": 0})
    by_status: Dict[str, int] = defaultdict(int)

    for t in tracks:
        tier = str(t.get("tier") or "?")
        status = str(t.get("status") or "unknown").lower()
        by_tier[tier]["total"] += 1
        if status == "live":
            by_tier[tier]["live"] += 1
        elif status == "shipped":
            by_tier[tier]["shipped"] += 1
        by_status[status] += 1

    ledger_agg = _aggregate_ledger_for_tracks(tracks, since_days=since_days)
    total_usd = sum(m.get("revenue_usd", 0) or 0 for m in ledger_agg.values())
    total_tx = sum(m.get("transaction_count", 0) or 0 for m in ledger_agg.values())

    hosting = _hosting_metrics(since_days=since_days)
    hosting_usd = float(hosting.get("usd_total") or 0)
    casino = _casino_metrics(since_days=since_days)
    casino_usd = float(casino.get("revenue_usd") or 0)

    try:
        from backend.services.monetization_revenue_pulse_service import build_revenue_pulse
        pulse = build_revenue_pulse(since_days=since_days)
        ledger_total = (pulse.get("ledger") or {}).get("revenue_usd_total", 0)
        margin = pulse.get("blended_gross_margin")
    except Exception:
        ledger_total = total_usd
        margin = None

    return {
        "success": True,
        "north_star": get_north_star(),
        "generated_at": _iso_now(),
        "since_days": since_days,
        "summary": {
            "track_count": len(tracks),
            "by_tier": dict(by_tier),
            "by_status": dict(by_status),
            "ledger_attributed_usd": round(total_usd, 2),
            "ledger_total_usd": ledger_total,
            "hosting_usd": round(hosting_usd, 2),
            "casino_usd": round(casino_usd, 2),
            "combined_estimated_usd": round(max(total_usd, ledger_total) + hosting_usd + casino_usd, 2),
            "attributed_transactions": total_tx,
            "blended_gross_margin": margin,
        },
        "top_tracks_by_revenue": sorted(
            [
                {
                    "track_id": tid,
                    "name": next((t["name"] for t in tracks if t.get("id") == tid), tid),
                    **m,
                }
                for tid, m in ledger_agg.items()
                if (m.get("revenue_usd") or 0) > 0
            ],
            key=lambda x: -(x.get("revenue_usd") or 0),
        )[:10],
    }


def build_dashboard(*, since_days: float = 7) -> Dict[str, Any]:
    """Full admin dashboard — status + all tracks with metrics."""
    status = get_machine_status(since_days=since_days)
    catalog = list_tracks(include_metrics=True, since_days=since_days)
    return {
        "success": True,
        "generated_at": _iso_now(),
        "since_days": since_days,
        "machine": status,
        "tracks": catalog.get("tracks", []),
        "north_star": catalog.get("north_star", {}),
    }
