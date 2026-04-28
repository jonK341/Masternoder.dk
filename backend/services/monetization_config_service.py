"""
Single source for monetization JSON: packs, credit ↔ reference mapping, tier caps.

Loads data/monetization_config.json (project root). Override path with MONETIZATION_CONFIG_PATH.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _config_path() -> str:
    override = (os.environ.get("MONETIZATION_CONFIG_PATH") or "").strip()
    if override:
        return override
    return os.path.join(_project_root(), "data", "monetization_config.json")


@lru_cache(maxsize=1)
def _load_raw() -> Dict[str, Any]:
    path = _config_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def reload_monetization_config() -> None:
    """Clear cache after file edit (tests or hot reload)."""
    _load_raw.cache_clear()


def get_credit_reference_fraction() -> float:
    """How much of one reference job one abstract 'generation_credit' represents."""
    raw = _load_raw()
    cd = raw.get("credit_definition") or {}
    return float(cd.get("reference_fraction_per_credit") or 0.25)


def get_coin_packs() -> List[Dict[str, Any]]:
    """PayPal coin packs (same shape as legacy PAYPAL_COIN_PACKS + optional generation_credits_granted)."""
    raw = _load_raw()
    packs = raw.get("coin_packs")
    if isinstance(packs, list) and len(packs) > 0:
        return list(packs)
    return []


def get_coin_pack_map() -> Dict[str, Dict[str, Any]]:
    return {p["id"]: p for p in get_coin_packs() if p.get("id")}


def get_tier_caps(tier_id: str) -> Dict[str, Any]:
    raw = _load_raw()
    tiers = raw.get("tiers") or {}
    tid = (tier_id or "").strip().lower() or str(raw.get("default_tier") or "creator")
    t = tiers.get(tid) or tiers.get("creator") or {}
    return dict(t) if isinstance(t, dict) else {}


def get_default_tier_id() -> str:
    raw = _load_raw()
    return str(raw.get("default_tier") or "creator").strip().lower() or "creator"


def list_subscription_plan_ids() -> List[str]:
    """PayPal billing plan ids (P-…) defined under subscriptions.plans."""
    raw = _load_raw()
    plans = ((raw.get("subscriptions") or {}).get("plans")) or {}
    if not isinstance(plans, dict):
        return []
    return [str(k) for k in plans.keys() if k]


def get_b2b_studio_skus() -> List[Dict[str, Any]]:
    """SCR quote anchors from b2b_studio_skus.skus."""
    raw = _load_raw()
    block = raw.get("b2b_studio_skus") or {}
    skus = block.get("skus") if isinstance(block, dict) else None
    if not isinstance(skus, list):
        return []
    out: List[Dict[str, Any]] = []
    for s in skus:
        if isinstance(s, dict) and s.get("id"):
            out.append(dict(s))
    return out


def get_b2b_studio_sku_map() -> Dict[str, Dict[str, Any]]:
    return {str(s["id"]): s for s in get_b2b_studio_skus() if s.get("id")}


def get_b2b_studio_sku(sku_id: str) -> Dict[str, Any]:
    return dict(get_b2b_studio_sku_map().get((sku_id or "").strip()) or {})


def get_subscription_plan(plan_id: str) -> Dict[str, Any]:
    """PayPal plan id (P-…) → monthly credits / tier label from monetization_config.subscriptions.plans."""
    raw = _load_raw()
    subs = raw.get("subscriptions") or {}
    plans = subs.get("plans") or {}
    if not isinstance(plans, dict):
        return {}
    pid = (plan_id or "").strip()
    p = plans.get(pid)
    return dict(p) if isinstance(p, dict) else {}


def get_public_config() -> Dict[str, Any]:
    """Safe for API: no secrets."""
    raw = _load_raw()
    subs = raw.get("subscriptions") or {}
    plans_out: Dict[str, Any] = {}
    if isinstance(subs, dict):
        plans = subs.get("plans") or {}
        if isinstance(plans, dict):
            for pid, p in plans.items():
                if not isinstance(p, dict):
                    continue
                plans_out[pid] = {
                    "label": p.get("label"),
                    "price_usd_monthly": p.get("price_usd_monthly"),
                    "monthly_generation_credits": p.get("monthly_generation_credits"),
                    "monthly_coins_granted": p.get("monthly_coins_granted"),
                    "tier": p.get("tier"),
                }
    scr_out: List[Dict[str, Any]] = []
    for s in get_b2b_studio_skus():
        scr_out.append({
            "id": s.get("id"),
            "label": s.get("label"),
            "description": s.get("description"),
            "term_days": s.get("term_days"),
            "generation_credits_pool": s.get("generation_credits_pool"),
            "list_price_usd": s.get("list_price_usd"),
            "currency": s.get("currency") or "USD",
        })
    return {
        "reference_job_id": raw.get("reference_job_id"),
        "credit_definition": raw.get("credit_definition"),
        "coin_packs": get_coin_packs(),
        "tiers": list((raw.get("tiers") or {}).keys()),
        "default_tier": get_default_tier_id(),
        "subscriptions": {"plans": plans_out},
        "b2b_studio_skus": scr_out,
    }
