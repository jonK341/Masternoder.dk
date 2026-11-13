"""Four canonical profit-body strategy categories.

These are the top-level families the limbs enrich against — not every addon
profile. Profiles in ``profit_trading_profiles`` map into one of these.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Canonical four — user-facing strategy families for the profit body.
STRATEGY_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "arbitrage": {
        "id": "arbitrage",
        "name": "Arbitrage Trading",
        "name_da": "Arbitragehandel",
        "summary": (
            "Buy a crypto cheap on one venue and sell it immediately richer on another. "
            "Low paper risk; needs fast execution and capital split across platforms."
        ),
        "summary_da": (
            "Køb billigt på én børs og sælg øjeblikkeligt dyrere på en anden. "
            "Lav risiko på papiret; kræver hurtig eksekvering og kapital på flere platforme."
        ),
        "limbs": [
            "hunter", "dual_farm", "latch", "executor", "datamaxi",
            "courier", "pbook", "closer",
        ],
        "profiles": [
            "spatial_taker_cut",
            "skew_maker_latch",
            "quote_bridge_courier",
            "datamaxi_cex_spread",
            "triangular_cycle",
            "hummingbot_spot_perp_basis",
        ],
        "risk": "execution_latency_and_split_capital",
        "enrichment_keys": ["edge_band", "cut_bps", "mid_skew_bps", "route", "net_bps"],
    },
    "momentum": {
        "id": "momentum",
        "name": "Momentum Trading",
        "name_da": "Momentumhandel",
        "summary": (
            "Buy names with strong short-term price rise and high volume "
            "(news / market sentiment). Fast profit window; requires a tight stop-loss."
        ),
        "summary_da": (
            "Køb kryptovalutaer med stærk kortsigtet prisstigning og høj volumen "
            "baseret på nyheder eller markedsstemning. Hurtig profit; kræver stramt stop-loss."
        ),
        "limbs": ["momentum", "swing"],
        "profiles": ["momentum_volume_burst", "precision_level_swing"],
        "risk": "sentiment_reversal_needs_tight_stop",
        "enrichment_keys": [
            "momentum_score", "return_bps", "volume_ratio", "stop_pct", "bias",
        ],
    },
    "vwap": {
        "id": "vwap",
        "name": "VWAP Strategy",
        "name_da": "VWAP-strategi",
        "summary": (
            "Use volume-weighted average price as dynamic intraday support/resistance. "
            "Institutions judge cheap vs rich relative to today's volume."
        ),
        "summary_da": (
            "Brug den volumen-vægtede gennemsnitspris som dynamisk støtte/modstand "
            "til intradag-handel — billigt eller dyrt ift. dagens volumen."
        ),
        "limbs": ["vwap", "grid", "latch"],
        "profiles": ["vwap_intraday_levels"],
        "risk": "trend_days_vwap_chase",
        "enrichment_keys": ["vwap", "distance_bps", "session_bias", "bands"],
    },
    "grid": {
        "id": "grid",
        "name": "Grid Trading",
        "name_da": "Gitterhandel",
        "summary": (
            "Automated buy/sell ladder at fixed intervals around mid. Harvests "
            "sideways noise; binds capital if price trends hard against the book."
        ),
        "summary_da": (
            "Automatiseret net af købs- og salgsordrer med faste intervaller. "
            "Tjener på sidelæns støj; binder kapital ved kraftige trends."
        ),
        "limbs": ["grid", "closer", "courier"],
        "profiles": ["grid_range_harvest", "hummingbot_cross_exchange_mm"],
        "risk": "capital_bound_on_trend",
        "enrichment_keys": ["open_orders", "realized", "thin_quote", "universe"],
    },
}


def list_categories() -> List[Dict[str, Any]]:
    return [dict(v) for v in STRATEGY_CATEGORIES.values()]


def category_for_limb(limb: str) -> Optional[Dict[str, Any]]:
    name = str(limb or "").strip().lower()
    for cat in STRATEGY_CATEGORIES.values():
        if name in (cat.get("limbs") or []):
            return dict(cat)
    return None


def categories_for_profile(profile_id: str) -> List[Dict[str, Any]]:
    pid = str(profile_id or "").strip()
    out: List[Dict[str, Any]] = []
    for cat in STRATEGY_CATEGORIES.values():
        if pid in (cat.get("profiles") or []):
            out.append(dict(cat))
    return out


def limb_category_map() -> Dict[str, str]:
    """limb → primary category id (first match wins)."""
    out: Dict[str, str] = {}
    for cid, cat in STRATEGY_CATEGORIES.items():
        for limb in cat.get("limbs") or []:
            out.setdefault(str(limb), cid)
    return out
