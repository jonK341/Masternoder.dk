"""Distribution-channel income streams — Google Play, Discord, Facebook, YouTube, podcast hub."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STREAMS_PATH = os.path.join(_BASE, "data", "monetization_streams.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@lru_cache(maxsize=1)
def _load_streams_doc() -> Dict[str, Any]:
    if not os.path.isfile(_STREAMS_PATH):
        return {"streams": []}
    try:
        with open(_STREAMS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"streams": []}
    except Exception:
        return {"streams": []}


def reload_streams() -> None:
    _load_streams_doc.cache_clear()


def list_distribution_streams() -> List[Dict[str, Any]]:
    doc = _load_streams_doc()
    streams = doc.get("streams") or []
    return [dict(s) for s in streams if isinstance(s, dict) and s.get("id")]


def _stream_readiness(stream: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight readiness probe per stream (no external network)."""
    sid = stream.get("id", "")
    ready = stream.get("status") == "live" and stream.get("enabled", True) is not False
    notes: List[str] = []

    if sid == "google-play-casino":
        try:
            from backend.services.mobile_iap_service import public_catalog

            cat = public_catalog()
            ready = ready and bool(cat.get("products") or cat.get("catalog"))
            notes.append(f"IAP SKUs: {len(cat.get('products') or cat.get('catalog') or [])}")
        except Exception as exc:
            notes.append(f"mobile_iap: {exc}")
    elif sid == "discord-casino-full":
        manifest = os.path.join(_BASE, "data", "discord_app_manifest.json")
        ready = ready and os.path.isfile(manifest)
        token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
        notes.append("bot_token_configured" if token else "bot_token_missing")
    elif sid == "facebook-casino":
        cfg = os.path.join(_BASE, "data", "facebook_casino_bot_config.json")
        ready = ready and os.path.isfile(cfg)
        token = (os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()
        notes.append("page_token_configured" if token else "page_token_missing")
    elif sid == "youtube-monetization":
        pod = os.path.join(_BASE, "data", "podcast_episodes.json")
        if os.path.isfile(pod):
            with open(pod, "r", encoding="utf-8") as f:
                eps = json.load(f).get("episodes") or []
            yt = sum(
                1 for e in eps
                if isinstance(e, dict) and (e.get("platform_links") or {}).get("youtube")
            )
            notes.append(f"episodes_with_youtube: {yt}")
        else:
            notes.append("podcast_episodes_missing")
    elif sid == "ipodcast-premium":
        try:
            from backend.services.monetization_config_service import get_public_config

            cfg = get_public_config()
            skus = [
                s for s in (cfg.get("shop_skus") or [])
                if isinstance(s, dict) and "podcast" in str(s.get("id", "")).lower()
            ]
            notes.append(f"podcast_skus: {len(skus)}")
        except Exception:
            pass
    elif sid == "masternode-hosting":
        try:
            from backend.services import mn2_masternode_service as mn

            st = mn.get_service_status()
            notes.append(f"slots_available: {st.get('slots_available', 0)}")
        except Exception:
            pass

    return {"ready": ready, "notes": notes}


def stream_hub(*, include_metrics: bool = True) -> Dict[str, Any]:
    streams = list_distribution_streams()
    rows: List[Dict[str, Any]] = []
    for s in streams:
        entry = {k: s.get(k) for k in (
            "id", "name", "category", "status", "priority", "enabled",
            "description", "payment_rails", "revenue_track_ids",
            "checkout_url", "api_status", "icon", "price", "recurring", "interval", "features",
        )}
        entry["readiness"] = _stream_readiness(s)
        if include_metrics:
            entry["metrics"] = _stream_metrics(s)
        rows.append(entry)

    rows.sort(key=lambda r: int(r.get("priority") or 99))
    try:
        from backend.services.monetization_activity_queue_service import queue_stats

        activity = queue_stats()
    except Exception:
        activity = {}

    return {
        "success": True,
        "version": _load_streams_doc().get("version", "1.0.0"),
        "stream_count": len(rows),
        "enabled_count": sum(1 for r in rows if r.get("enabled", True) is not False and r.get("status") == "live"),
        "streams": rows,
        "activity_queue": activity,
        "generated_at": _iso(),
    }


def _stream_metrics(stream: Dict[str, Any]) -> Dict[str, Any]:
    track_ids = stream.get("revenue_track_ids") or []
    if not track_ids:
        return {}
    try:
        from backend.services.monetization_revenue_tracks_service import get_track_metrics

        total_usd = 0.0
        tx = 0
        tracks: List[Dict[str, Any]] = []
        for tid in track_ids[:3]:
            m = get_track_metrics(str(tid), since_days=30)
            if not m.get("success"):
                continue
            metrics = m.get("metrics") or {}
            rev = metrics.get("revenue_usd")
            if rev is not None:
                total_usd += float(rev or 0)
            tx += int(metrics.get("transaction_count") or 0)
            tracks.append({"track_id": tid, "metrics": metrics})
        return {
            "revenue_usd_30d": round(total_usd, 2),
            "transaction_count_30d": tx,
            "tracks": tracks,
        }
    except Exception:
        return {}


def build_top_25_streams() -> List[Dict[str, Any]]:
    """Merge distribution streams + revenue-track fillers for monetization page."""
    dist = list_distribution_streams()
    top: List[Dict[str, Any]] = []
    for s in sorted(dist, key=lambda x: int(x.get("priority") or 99)):
        top.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "category": s.get("category", "distribution"),
            "description": s.get("description", ""),
            "price": float(s.get("price") or 0),
            "recurring": bool(s.get("recurring")),
            "interval": s.get("interval") or "month",
            "enabled": s.get("enabled", True) is not False and s.get("status") == "live",
            "priority": int(s.get("priority") or len(top) + 1),
            "features": s.get("features") or [],
            "payment_rails": s.get("payment_rails") or [],
            "checkout_url": s.get("checkout_url"),
            "icon": s.get("icon"),
        })

    try:
        from backend.services.monetization_revenue_tracks_service import list_track_definitions

        tracks = list_track_definitions()
        filler_priority = len(top) + 1
        for t in tracks:
            if len(top) >= 25:
                break
            if t.get("status") not in ("live", "shipped"):
                continue
            tid = t.get("id", "")
            if any(str(x.get("id", "")).startswith(tid) for x in top):
                continue
            if tid in ("A3", "A9", "D3"):
                continue
            top.append({
                "id": f"track-{tid.lower()}",
                "name": t.get("name"),
                "category": f"tier_{str(t.get('tier', 'x')).lower()}",
                "description": f"Revenue track {tid} — {t.get('revenue_model', 'mixed')}",
                "price": 0,
                "recurring": t.get("revenue_model") == "subscription",
                "interval": "month",
                "enabled": t.get("status") == "live",
                "priority": filler_priority,
                "features": [f"Track {tid}", str(t.get("metric_source") or "ledger")],
                "payment_rails": ["paypal", "mn2"],
            })
            filler_priority += 1
    except Exception:
        pass

    top.sort(key=lambda x: x.get("priority", 99))
    return top[:25]


def build_recap() -> Dict[str, Any]:
    hub = stream_hub(include_metrics=True)
    streams = hub.get("streams") or []
    total_revenue = sum(
        float((s.get("metrics") or {}).get("revenue_usd_30d") or 0) for s in streams
    )
    monthly_potential = sum(
        float(s.get("price") or 0) for s in streams
        if s.get("recurring") and s.get("enabled", True) is not False
    )
    enabled = hub.get("enabled_count", 0)
    return {
        "success": True,
        "total_streams": len(streams),
        "enabled_streams": enabled,
        "revenue_stats": {
            "total_revenue": round(total_revenue, 2),
            "period_days": 30,
        },
        "potential_monthly_revenue": {
            "monthly_recurring_potential": round(monthly_potential, 2),
        },
        "activity_queue": hub.get("activity_queue") or {},
        "distribution_streams": len(list_distribution_streams()),
        "generated_at": _iso(),
    }
