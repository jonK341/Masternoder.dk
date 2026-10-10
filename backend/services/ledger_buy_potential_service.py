"""Ledger customer buy potential — spending signals, tiers, and purchase suggestions."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BUY_SPEND_TYPES = frozenset({
    "shop_payment",
    "onramp_purchase",
    "p2p_buy",
    "p2p_market_buy",
    "encoder_payment",
    "generator_payment",
    "gallery_premium_unlock",
    "masternode_hosting_payment",
    "swap_buy",
    "aggregator_callback_bet",
})

FUNDING_INFLOW_TYPES = frozenset({
    "deposit",
    "onramp_purchase",
    "staking_reward",
    "aggregator_mn2_earn",
    "p2p_sell_escrow",
    "trophy_reward",
})


def _config() -> Dict[str, Any]:
    try:
        with open(os.path.join(_BASE, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            root = json.load(f)
        block = root.get("ledger_customer_control") if isinstance(root, dict) else {}
        bp = block.get("buy_potential") if isinstance(block, dict) else {}
        return bp if isinstance(bp, dict) else {}
    except Exception:
        return {}


def _purchase_catalog() -> List[Dict[str, Any]]:
    cfg_path = os.path.join(_BASE, "data", "mn2_config.json")
    items: List[Dict[str, Any]] = []
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            root = json.load(f)
        gen = root.get("generator") if isinstance(root, dict) else {}
        if isinstance(gen, dict):
            for key, label in (
                ("earn_on_finish_mn2", "Generator finish"),
                ("express_pack_mn2", "Generator express pack"),
                ("premium_encode_mn2", "Premium encode"),
                ("ultra_encode_mn2", "Ultra encode"),
            ):
                price = float(gen.get(key) or 0)
                if price > 0:
                    items.append({"sku": key, "label": label, "price_mn2": price, "category": "encoder"})
        enc = root.get("encoder_customer_fulfillment") if isinstance(root, dict) else {}
        bonus = float((enc or {}).get("bonus_mn2") or 0)
        if bonus > 0:
            items.append({"sku": "encoder_fulfillment_bonus", "label": "Encoder fulfillment bundle", "price_mn2": bonus, "category": "encoder"})
    except Exception:
        pass
    items.sort(key=lambda r: float(r.get("price_mn2") or 0))
    return items


def suggest_purchases(spendable_mn2: float) -> List[Dict[str, Any]]:
    """What this customer can afford right now from known MN2-priced SKUs."""
    bal = max(0.0, float(spendable_mn2 or 0))
    out: List[Dict[str, Any]] = []
    for item in _purchase_catalog():
        price = float(item.get("price_mn2") or 0)
        if price <= 0:
            continue
        out.append({
            **item,
            "affordable": bal >= price,
            "shortfall_mn2": round(max(0.0, price - bal), 8),
        })
    affordable = [r for r in out if r.get("affordable")]
    return affordable[:5] if affordable else out[:3]


def classify_buy_tier(
    *,
    spendable_mn2: float,
    buy_spend_mn2: float,
    buy_count: int,
    has_bought: bool,
    has_funding: bool,
) -> str:
    cfg = _config()
    high_spender = float(cfg.get("high_spender_mn2") or 0.5)
    min_spend = float(cfg.get("min_spendable_mn2") or 0.01)

    if buy_spend_mn2 >= high_spender or buy_count >= 5:
        return "high_spender"
    if has_bought and buy_count >= 2:
        return "repeat_buyer"
    if has_bought and spendable_mn2 >= min_spend:
        return "active_buyer"
    if has_bought:
        return "lapsed_buyer"
    if spendable_mn2 >= min_spend or (has_funding and spendable_mn2 > 0):
        return "funded_never_bought"
    if has_funding:
        return "funded_never_bought"
    return "needs_funding"


def enrich_ledger_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    """Attach buy-potential fields to a ledger summary row (no live wallet lookup)."""
    spendable = float(row.get("ledger_net_mn2") or 0)
    buy_spend = float(row.get("buy_spend_mn2") or 0)
    buy_count = int(row.get("buy_count") or 0)
    has_bought = bool(row.get("has_bought"))
    has_funding = bool(row.get("has_funding"))
    tier = classify_buy_tier(
        spendable_mn2=spendable,
        buy_spend_mn2=buy_spend,
        buy_count=buy_count,
        has_bought=has_bought,
        has_funding=has_funding,
    )
    enriched = dict(row)
    enriched["buy_potential"] = {
        "tier": tier,
        "spendable_mn2": round(spendable, 8),
        "buy_spend_mn2": round(buy_spend, 8),
        "buy_count": buy_count,
        "has_bought": has_bought,
        "buy_channels": list(row.get("buy_channels") or []),
        "suggested_purchases": suggest_purchases(spendable),
    }
    return enriched


def compute_buy_potential(user_id: str, *, live_balance: bool = True) -> Dict[str, Any]:
    """Full buy-potential view for one customer."""
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id_required"}

    from backend.services.ledger_customer_aggregator_service import load_ledger_customer_rows

    row = None
    for candidate in load_ledger_customer_rows():
        if candidate.get("user_id") == uid:
            row = dict(candidate)
            break

    if not row:
        from backend.services.mn2_ledger import get_entries_by_user

        entries = get_entries_by_user(uid, limit=500)
        if not entries:
            return {"success": False, "error": "not_found", "user_id": uid}
        from backend.services.mn2_ledger import _summarize_entries_for_user

        row = _summarize_entries_for_user(uid, entries)

    spendable = float(row.get("ledger_net_mn2") or 0)
    if live_balance:
        try:
            from backend.services.mn2_hold_registry import get_holds

            holds = get_holds(uid)
            spendable = float(holds.get("liquid_mn2") or spendable)
        except Exception:
            pass

    buy_spend = float(row.get("buy_spend_mn2") or 0)
    buy_count = int(row.get("buy_count") or 0)
    has_bought = bool(row.get("has_bought"))
    has_funding = bool(row.get("has_funding"))
    tier = classify_buy_tier(
        spendable_mn2=spendable,
        buy_spend_mn2=buy_spend,
        buy_count=buy_count,
        has_bought=has_bought,
        has_funding=has_funding,
    )

    return {
        "success": True,
        "user_id": uid,
        "buy_potential": {
            "tier": tier,
            "spendable_mn2": round(spendable, 8),
            "buy_spend_mn2": round(buy_spend, 8),
            "buy_count": buy_count,
            "has_bought": has_bought,
            "buy_channels": list(row.get("buy_channels") or []),
            "last_buy_at": row.get("last_buy_at"),
            "suggested_purchases": suggest_purchases(spendable),
            "catalog": _purchase_catalog(),
        },
        "ledger": row,
    }


def list_buy_opportunities(
    *,
    limit: int = 50,
    offset: int = 0,
    tier: Optional[str] = None,
    sort: str = "spendable",
) -> Dict[str, Any]:
    """Rank ledger customers by buy potential for ops targeting."""
    from backend.services.ledger_customer_aggregator_service import load_ledger_customer_rows

    rows = []
    for r in load_ledger_customer_rows():
        rows.append(dict(r) if r.get("buy_potential") else enrich_ledger_summary(dict(r)))
    tier_filter = (tier or "").strip().lower()
    if tier_filter:
        rows = [
            r for r in rows
            if str((r.get("buy_potential") or {}).get("tier") or "").lower() == tier_filter
        ]

    if sort == "spend":
        rows.sort(key=lambda r: float((r.get("buy_potential") or {}).get("buy_spend_mn2") or 0), reverse=True)
    elif sort == "recent_buy":
        rows.sort(key=lambda r: str(r.get("last_buy_at") or r.get("last_activity") or ""), reverse=True)
    else:
        rows.sort(
            key=lambda r: float((r.get("buy_potential") or {}).get("spendable_mn2") or 0),
            reverse=True,
        )

    total = len(rows)
    page = rows[offset: offset + limit]
    return {"success": True, "customers": page, "total": total, "limit": limit, "offset": offset, "tier": tier_filter or None}


def buy_potential_stats() -> Dict[str, Any]:
    from backend.services.ledger_customer_aggregator_service import (
        ledger_customer_index_meta,
        load_ledger_customer_rows,
    )

    rows = list(load_ledger_customer_rows())
    by_tier: Dict[str, int] = {}
    total_spendable = 0.0
    funded_never_bought = 0
    for raw in rows:
        row = raw if (raw.get("buy_potential")) else enrich_ledger_summary(dict(raw))
        bp = row.get("buy_potential") or {}
        t = str(bp.get("tier") or "unknown")
        by_tier[t] = by_tier.get(t, 0) + 1
        total_spendable += float(bp.get("spendable_mn2") or 0)
        if t == "funded_never_bought":
            funded_never_bought += 1

    meta = ledger_customer_index_meta()
    return {
        "success": True,
        "index": meta,
        "total_customers": len(rows),
        "by_tier": by_tier,
        "funded_never_bought": funded_never_bought,
        "total_estimated_spendable_mn2": round(total_spendable, 8),
        "purchase_catalog": _purchase_catalog(),
    }


def nudge_buy_tier(
    *,
    tier: str = "funded_never_bought",
    limit: int = 10,
) -> Dict[str, Any]:
    """Run AI nudge on top buy-opportunity customers in a tier (uses assigned controller)."""
    from backend.services.ledger_customer_control_service import execute_control_action, get_assignment

    opps = list_buy_opportunities(limit=limit, offset=0, tier=tier, sort="spendable")
    results: List[Dict[str, Any]] = []
    for row in (opps.get("customers") or []):
        uid = row.get("user_id")
        if not uid:
            continue
        bp = row.get("buy_potential") or {}
        suggestions = bp.get("suggested_purchases") or []
        payload = {
            "metadata": {
                "buy_potential_tier": bp.get("tier"),
                "suggested_purchases": suggestions[:3],
                "spendable_mn2": bp.get("spendable_mn2"),
            }
        }
        if not get_assignment(uid):
            execute_control_action(uid, "onboard", approved=True, payload=payload)
        res = execute_control_action(uid, "nudge", approved=True, payload=payload)
        results.append({"user_id": uid, "tier": bp.get("tier"), "result": res})

    return {
        "success": True,
        "tier": tier,
        "nudged_count": len(results),
        "results_preview": results[:10],
    }
