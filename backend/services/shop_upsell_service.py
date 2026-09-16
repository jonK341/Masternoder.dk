"""Tier C2 — post-purchase upsell suggestions for shop PayPal return."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def upsell_suggestions(
    *,
    item_id: str = "",
    coins_granted: int = 0,
    purchase_kind: str = "",
) -> List[Dict[str, str]]:
    iid = (item_id or "").strip().lower()
    kind = (purchase_kind or "").strip().lower()
    out: List[Dict[str, str]] = []

    if kind == "coin_pack" or iid.startswith("coin-pack"):
        out.append({
            "title": "MN2 starter bundle",
            "desc": "500 coins + 7-day staking boost + badge",
            "href": "/shop?tab=catalog",
            "cta": "View bundle",
        })
        out.append({
            "title": "Masternode hosting",
            "desc": "Reserve a slot — $4.99/slot via PayPal or MN2",
            "href": "/shop?tab=mn2",
            "cta": "Host MN2",
        })
    elif kind == "hosting" or iid.startswith("mnq_"):
        out.append({
            "title": "Staking Surge x2 (6h)",
            "desc": "Boost pool rewards after your node is live",
            "href": "/shop?tab=catalog",
            "cta": "Get booster",
        })
        out.append({
            "title": "Explorer market",
            "desc": "Trade MN2 for coins on the internal market",
            "href": "/explorer?tab=market",
            "cta": "Open market",
        })
    elif iid.startswith("bundle-booster") or "booster" in iid:
        out.append({
            "title": "Camgirls studio",
            "desc": "Tip performers with your boosted coin balance",
            "href": "/camgirls/",
            "cta": "Browse performers",
        })
    else:
        out.append({
            "title": "Generator credits",
            "desc": "Turn coins into video generation jobs",
            "href": "/generator/",
            "cta": "Open generator",
        })

    if coins_granted >= 500:
        out.insert(0, {
            "title": "VIP Pass — 30 days",
            "desc": "Daily coin claim + catalog discount",
            "href": "/shop?tab=catalog",
            "cta": "See VIP pass",
        })

    return out[:3]
