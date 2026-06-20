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


def credits_to_ref_eq_generations(credits: float) -> float:
    """Reference-equivalent generations for N generation credits (see REFERENCE_JOB_COGS.md)."""
    frac = get_credit_reference_fraction()
    if frac <= 0:
        return 0.0
    return round(float(credits or 0) * frac, 2)


def ratio_to_credits_used(ratio: float) -> float:
    """Generation credits consumed for a job with ratio_vs_reference_job."""
    frac = get_credit_reference_fraction()
    if frac <= 0:
        return round(float(ratio or 0), 4)
    return round(float(ratio or 0) / frac, 4)


def ref_eq_label(credits: float) -> str:
    """Human label for shop copy, e.g. '≈ 1.5 ref-eq generations'."""
    n = credits_to_ref_eq_generations(credits)
    if n <= 0:
        return ""
    g = f"{n:g}"
    word = "generation" if n == 1 else "generations"
    return f"≈ {g} ref-eq {word}"


def enrich_coin_pack(pack: Dict[str, Any]) -> Dict[str, Any]:
    """Add reference-equivalent fields for PayPal pack display."""
    row = dict(pack)
    gc = pack.get("generation_credits_granted")
    if gc is not None:
        try:
            credits = float(gc)
        except (TypeError, ValueError):
            credits = 0.0
        row["reference_equivalent_generations"] = credits_to_ref_eq_generations(credits)
        label = ref_eq_label(credits)
        if label:
            row["reference_eq_label"] = label
    return row


def get_coin_packs() -> List[Dict[str, Any]]:
    """PayPal coin packs (same shape as legacy PAYPAL_COIN_PACKS + optional generation_credits_granted)."""
    raw = _load_raw()
    packs = raw.get("coin_packs")
    if isinstance(packs, list) and len(packs) > 0:
        return list(packs)
    return []


def is_overage_pack(pack: Dict[str, Any]) -> bool:
    tag = str(pack.get("tag") or "").strip().lower()
    kind = str(pack.get("kind") or "").strip().lower()
    return tag == "overage" or kind == "overage"


def get_overage_packs() -> List[Dict[str, Any]]:
    """PayPal SKUs for subscription overage top-ups (tag=overage)."""
    return [enrich_coin_pack(dict(p)) for p in get_coin_packs() if is_overage_pack(p)]


def get_retail_coin_packs() -> List[Dict[str, Any]]:
    """Standard shop coin packs (excludes overage top-ups)."""
    return [enrich_coin_pack(dict(p)) for p in get_coin_packs() if not is_overage_pack(p)]


def get_overage_policy() -> Dict[str, Any]:
    raw = _load_raw()
    block = raw.get("overage_policy")
    return dict(block) if isinstance(block, dict) else {"show_offers_from_percent": 80}


def get_payment_rails_catalog() -> Dict[str, Any]:
    """Rails defaults + sku_overrides from monetization_config (Phase 1 content/crypto plan)."""
    raw = _load_raw()
    block = raw.get("payment_rails_catalog")
    if isinstance(block, dict):
        return dict(block)
    return {"rails": ["paypal", "mn2", "credits"], "defaults": {}, "sku_overrides": {}}


def get_digital_goods() -> List[Dict[str, Any]]:
    """Lawful digital SKUs (themes, prompts, docs placeholders); delivery wired in Phase 2."""
    raw = _load_raw()
    dg = raw.get("digital_goods")
    if not isinstance(dg, list):
        return []
    out: List[Dict[str, Any]] = []
    for x in dg:
        if isinstance(x, dict) and x.get("id"):
            out.append(dict(x))
    return out


def get_public_digital_goods() -> List[Dict[str, Any]]:
    """Digital goods catalog safe for API responses (no server-relative artifact paths)."""
    public: List[Dict[str, Any]] = []
    for good in get_digital_goods():
        row = dict(good)
        row.pop("artifact_path", None)
        public.append(row)
    return public


def get_mn2_services() -> List[Dict[str, Any]]:
    """MN2 platform services surfaced in shop (hosting, on-ramp, staking links)."""
    raw = _load_raw()
    services = raw.get("mn2_services")
    if not isinstance(services, list):
        return []
    out: List[Dict[str, Any]] = []
    for x in services:
        if isinstance(x, dict) and x.get("id"):
            out.append(dict(x))
    return out


def get_public_mn2_services() -> List[Dict[str, Any]]:
    """MN2 services safe for API responses."""
    return [dict(s) for s in get_mn2_services()]


def get_content_bundles() -> List[Dict[str, Any]]:
    """Configured bundles that combine credits/coins and digital goods into one SKU."""
    raw = _load_raw()
    bundles = raw.get("content_bundles")
    if not isinstance(bundles, list):
        return []
    out: List[Dict[str, Any]] = []
    for x in bundles:
        if isinstance(x, dict) and x.get("id"):
            out.append(dict(x))
    return out


def get_public_content_bundles() -> List[Dict[str, Any]]:
    """Bundle catalog safe for API responses."""
    goods_by_id = {g.get("id"): g for g in get_public_digital_goods()}
    public: List[Dict[str, Any]] = []
    for bundle in get_content_bundles():
        row = dict(bundle)
        items = []
        for entry in row.get("items") or []:
            if not isinstance(entry, dict):
                continue
            iid = entry.get("item_id")
            item = {"item_id": iid, "quantity": int(entry.get("quantity") or 1)}
            if iid in goods_by_id:
                item["name"] = goods_by_id[iid].get("name")
                item["delivery"] = goods_by_id[iid].get("delivery")
            items.append(item)
        row["items"] = items
        public.append(row)
    return public


def get_coin_packs_with_payment_rails(*, include_overage: bool = True) -> List[Dict[str, Any]]:
    """Coin packs plus merged payment_rails per payment_rails_catalog."""
    packs = get_coin_packs()
    if not include_overage:
        packs = [p for p in packs if not is_overage_pack(p)]
    cat = get_payment_rails_catalog()
    defaults = cat.get("defaults") if isinstance(cat, dict) else None
    overrides = cat.get("sku_overrides") if isinstance(cat, dict) else None
    default_rails = None
    if isinstance(defaults, dict):
        default_rails = defaults.get("coin_pack")
    if not isinstance(default_rails, list):
        default_rails = ["paypal", "credits"]
    out: List[Dict[str, Any]] = []
    for p in packs:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        row = dict(p)
        orails = overrides.get(pid) if isinstance(overrides, dict) else None
        row["payment_rails"] = list(orails) if isinstance(orails, list) else list(default_rails)
        out.append(enrich_coin_pack(row))
    return out


def get_coin_pack_map() -> Dict[str, Dict[str, Any]]:
    return {p["id"]: p for p in get_coin_packs_with_payment_rails() if p.get("id")}


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


def get_shop_monetization() -> Dict[str, Any]:
    """Shop V9.2 monetization block: VIP pass, mystery boxes, spin wheel, flash sales, loyalty, gifting, auction feature."""
    raw = _load_raw()
    block = raw.get("shop_monetization")
    return dict(block) if isinstance(block, dict) else {}


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
                mgen = p.get("monthly_generation_credits")
                mgen_f = float(mgen) if mgen is not None else 0.0
                plans_out[pid] = {
                    "label": p.get("label"),
                    "price_usd_monthly": p.get("price_usd_monthly"),
                    "monthly_generation_credits": p.get("monthly_generation_credits"),
                    "monthly_coins_granted": p.get("monthly_coins_granted"),
                    "tier": p.get("tier"),
                    "reference_equivalent_generations_monthly": credits_to_ref_eq_generations(mgen_f),
                    "reference_eq_label_monthly": ref_eq_label(mgen_f) or None,
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
    prc = get_payment_rails_catalog()
    public_prc = {
        "rails": prc.get("rails"),
        "defaults": prc.get("defaults"),
        "sku_overrides": prc.get("sku_overrides"),
        "comment": prc.get("comment"),
    }
    return {
        "reference_job_id": raw.get("reference_job_id"),
        "credit_definition": raw.get("credit_definition"),
        "coin_packs": get_coin_packs_with_payment_rails(),
        "payment_rails_catalog": public_prc,
        "digital_goods": get_public_digital_goods(),
        "content_bundles": get_public_content_bundles(),
        "tiers": list((raw.get("tiers") or {}).keys()),
        "default_tier": get_default_tier_id(),
        "subscriptions": {"plans": plans_out},
        "b2b_studio_skus": scr_out,
        "overage_packs": get_overage_packs(),
        "overage_policy": get_overage_policy(),
    }
