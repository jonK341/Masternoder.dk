"""
COGS-aware generation pack pricing suggestions from metering.jsonl p90.
"""
from __future__ import annotations

from typing import Any, Dict


def pricing_suggestion() -> Dict[str, Any]:
    try:
        from backend.services.cogs_metering_service import summarize_metering_jsonl, estimate_reference_job_usd
    except Exception as e:
        return {"success": False, "error": str(e)}

    metering = summarize_metering_jsonl()
    ref = estimate_reference_job_usd()
    ref_total = float(ref.get("total_usd") or 0.01)
    rv = metering.get("ratio_vs_reference_job") if isinstance(metering.get("ratio_vs_reference_job"), dict) else {}
    p90_ratio = float(rv.get("p90") or rv.get("p50") or 1.0)
    target_margin = 0.35
    suggested_usd_per_ref_job = round(ref_total * p90_ratio / max(0.01, (1.0 - target_margin)), 4)

    return {
        "success": True,
        "reference_job_usd": ref_total,
        "p90_ratio_vs_reference": p90_ratio,
        "target_gross_margin_pct": target_margin * 100,
        "suggested_retail_usd_per_reference_job": suggested_usd_per_ref_job,
        "metering_jobs": metering.get("count"),
        "note": "Advisory only — apply via monetization_config / shop SKUs manually or via ops cron.",
    }


def apply_suggested_pack_price(
    *,
    sku_key: str = "generation_pack_ref",
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Write suggested USD price into data/monetization_config.json coin_packs entry (if present).
    """
    sug = pricing_suggestion()
    if not sug.get("success"):
        return sug
    price = float(sug.get("suggested_retail_usd_per_reference_job") or 0)
    if price <= 0:
        return {"success": False, "error": "invalid suggested price"}

    import json
    import os

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "monetization_config.json",
    )
    if not os.path.isfile(path):
        return {"success": False, "error": "monetization_config.json not found", "suggested_usd": price}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
    except Exception as e:
        return {"success": False, "error": str(e)}

    packs = raw.get("coin_packs") if isinstance(raw.get("coin_packs"), list) else []
    updated = False
    for pack in packs:
        if not isinstance(pack, dict):
            continue
        if pack.get("id") == sku_key or pack.get("sku") == sku_key:
            pack["suggested_cogs_usd"] = price
            if not dry_run:
                pack["price_usd"] = price
            updated = True
            break

    if not updated:
        return {
            "success": False,
            "error": f"pack {sku_key!r} not found in coin_packs",
            "suggested_usd": price,
        }

    if dry_run:
        return {"success": True, "dry_run": True, "suggested_usd": price, "sku": sku_key}

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    try:
        from backend.services.monetization_config_service import _load_raw
        _load_raw.cache_clear()
    except Exception:
        pass
    return {"success": True, "applied_usd": price, "sku": sku_key}
