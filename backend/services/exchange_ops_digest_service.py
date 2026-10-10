"""Feature 10: ops digest with optional webhook/email on thresholds."""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_mn2_pool_service import pool_gaps
from backend.services.exchange_ops_service import (
    _asset_usd,
    append_digest_entry,
    load_config,
    ops_dashboard,
    pool_health_score,
    reconcile_wallets,
)


def _send_webhook(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not url:
        return {"skipped": True, "reason": "no_webhook_url"}
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"success": True, "status": resp.status}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def run_ops_digest(*, force: bool = False) -> Dict[str, Any]:
    cfg = load_config()
    digest_cfg = cfg.get("digest") or {}
    if not digest_cfg.get("enabled", True) and not force:
        return {"success": True, "skipped": True, "reason": "disabled"}

    health = pool_health_score()
    gaps = pool_gaps()
    gap_usd = sum(_asset_usd(s, a) for s, a in gaps.items())
    recon = reconcile_wallets()
    dash = ops_dashboard()

    alerts = []
    health_threshold = float(digest_cfg.get("health_alert_below") or 40)
    if health.get("score", 100) < health_threshold:
        alerts.append({
            "type": "low_health",
            "score": health.get("score"),
            "threshold": health_threshold,
        })

    mn2_gap_threshold = float(digest_cfg.get("mn2_gap_alert_usd") or 500)
    mn2_gap = _asset_usd("MN2", float(gaps.get("MN2") or 0))
    if mn2_gap > mn2_gap_threshold:
        alerts.append({
            "type": "mn2_pool_gap",
            "gap_usd": round(mn2_gap, 2),
            "threshold": mn2_gap_threshold,
        })

    if recon.get("issues"):
        alerts.append({"type": "reconciliation", "count": len(recon.get("issues") or [])})

    payload = {
        "health": health,
        "pool_gaps_usd": round(gap_usd, 2),
        "circuit_breaker": dash.get("circuit_breaker"),
        "alerts": alerts,
        "reconciliation_issues": len(recon.get("issues") or []),
    }

    append_digest_entry(payload)

    webhook_url = str(digest_cfg.get("webhook_url") or os.environ.get("OPS_DIGEST_WEBHOOK") or "")
    webhook_result = None
    if alerts and webhook_url:
        webhook_result = _send_webhook(webhook_url, {"alerts": alerts, "health": health})

    return {
        "success": True,
        "digest": payload,
        "alert_count": len(alerts),
        "webhook": webhook_result,
        "email_to": digest_cfg.get("email_to") or "",
    }
