"""Look-through catalog of profit-maker trading profiles.

Maps external / open-source strategy styles onto our profit-body limbs so we
can pick addons without guessing. Profiles are advisory — not auto-wired.

Canonical families live in ``profit_strategy_categories`` (arbitrage,
momentum, vwap, grid). Each profile carries a ``category`` id.
"""
from __future__ import annotations

from typing import Any, Dict, List

from backend.config.profit_strategy_categories import STRATEGY_CATEGORIES, list_categories

# Body limbs these profiles may attach to.
_LIMBS = (
    "hunter", "dual_farm", "courier", "latch", "closer", "executor", "pbook",
    "grid", "head", "datamaxi", "basis", "swing", "momentum", "vwap",
)

PROFIT_TRADING_PROFILES: Dict[str, Dict[str, Any]] = {
    "precision_level_swing": {
        "name": "Precision level swing",
        "source": "classic floor pivots + swing H/L",
        "style": "swing_ta",
        "category": "momentum",
        "limbs": ["swing", "grid", "latch", "momentum"],
        "when": "systematic TA with disciplined S/R / pivot entries",
        "notes": (
            "THIS is the repeatable swing system: trend bias from MA cross, "
            "entries at pivot S1/R1, stops beyond swing high/low — discipline + precision price levels."
        ),
        "fit": "installed",
    },
    "momentum_volume_burst": {
        "name": "Momentum volume burst",
        "source": "classic short-horizon momentum + volume confirmation",
        "style": "momentum",
        "category": "momentum",
        "limbs": ["momentum"],
        "when": "strong short-term return + volume spike; news/sentiment heat optional",
        "notes": (
            "Installed as `momentum` limb. Paper by default; MOMENTUM_LIVE=1 to arm. "
            "Always publishes a tight stop_pct (default 1.5%)."
        ),
        "fit": "installed",
    },
    "vwap_intraday_levels": {
        "name": "VWAP intraday levels",
        "source": "institutional session VWAP ±σ bands",
        "style": "vwap",
        "category": "vwap",
        "limbs": ["vwap", "grid", "latch"],
        "when": "intraday cheap/rich vs day volume-weighted average",
        "notes": (
            "Installed as `vwap` limb. Buy bias below VWAP, sell bias above; "
            "enriches pbook/grid with distance_bps + bands."
        ),
        "fit": "installed",
    },
    "spatial_taker_cut": {
        "name": "Spatial taker (cutting edge)",
        "source": "internal",
        "style": "cex_cex_arb",
        "category": "arbitrage",
        "limbs": ["hunter", "executor", "pbook"],
        "when": "cutting_edge.band == fire",
        "notes": "Market buy cheap / sell rich only when cut_bps clears floor after skew−noise.",
        "fit": "installed",
    },
    "skew_maker_latch": {
        "name": "Skew maker latch",
        "source": "internal + Hummingbot maker ideas",
        "style": "passive_maker",
        "category": "arbitrage",
        "limbs": ["latch", "grid"],
        "when": "cutting_edge.band == latch",
        "notes": "Park limit sell on rich venue while mid-skew compresses; strike when fire.",
        "fit": "installed",
    },
    "quote_bridge_courier": {
        "name": "Quote-bridge courier",
        "source": "internal",
        "style": "inventory",
        "category": "arbitrage",
        "limbs": ["courier", "executor"],
        "when": "unfunded top route / thin buy-venue quote",
        "notes": "Raise USDC/USDT on buy venue via inventory sells — bridge without wire transfer.",
        "fit": "installed",
    },
    "grid_range_harvest": {
        "name": "Grid range harvest",
        "source": "Bitsgap GRID / Hummingbot pure MM",
        "style": "grid",
        "category": "grid",
        "limbs": ["grid", "closer"],
        "when": "sideways book, quote funded",
        "notes": "Maker ladders; closer harvests dust. Pause on thin quote.",
        "addon_refs": ["https://bitsgap.com/", "https://hummingbot.org/"],
        "fit": "installed",
    },
    "hummingbot_spot_perp_basis": {
        "name": "Spot–perp basis / funding",
        "source": "Hummingbot spot_perpetual_arbitrage + DataMaxi funding",
        "style": "basis",
        "category": "arbitrage",
        "limbs": ["basis"],
        "when": "funding APR / basis divergence clears thresholds",
        "notes": "Installed as `basis` limb. Paper signals by default; FUNDING_BASIS_LIVE=1 for perp later.",
        "addon_refs": [
            "https://hummingbot.org/strategies/v1-strategies/spot-perpetual-arbitrage/",
            "https://docs.datamaxiplus.com/strategies/funding-rate-arb",
        ],
        "fit": "installed",
    },
    "hummingbot_cross_exchange_mm": {
        "name": "Cross-exchange market making",
        "source": "Hummingbot",
        "style": "mm",
        "category": "grid",
        "limbs": ["grid", "courier", "latch"],
        "when": "two venues, inventory on both",
        "notes": "Quote on one venue, hedge on the other — cousin of our latch+courier.",
        "addon_refs": ["https://hummingbot.org/strategies/cross-exchange-market-making/"],
        "fit": "medium",
    },
    "triangular_cycle": {
        "name": "Triangular arbitrage",
        "source": "internal engines + Drakkar triangular",
        "style": "tri_arb",
        "category": "arbitrage",
        "limbs": ["head"],
        "when": "single-venue cycle > fees",
        "notes": "Already in EXCHANGE_PROFIT_PROFILE=max engine set.",
        "addon_refs": ["https://github.com/Drakkar-Software/Triangular-Arbitrage"],
        "fit": "already_present",
    },
    "cryptohopper_marketplace": {
        "name": "Cryptohopper strategy marketplace",
        "source": "Cryptohopper",
        "style": "signal_marketplace",
        "category": "momentum",
        "limbs": ["head"],
        "when": "want external strategy templates / paper lab",
        "notes": "Strategy design lab + AI tools; good for browsing profiles, not raw BN↔NK spatial.",
        "addon_refs": ["https://www.cryptohopper.com/"],
        "fit": "browse",
    },
    "stoic_meta_regime": {
        "name": "Stoic Meta regime rotation",
        "source": "Stoic AI",
        "style": "portfolio_ai",
        "category": "momentum",
        "limbs": ["head"],
        "when": "hands-off multi-strategy allocation",
        "notes": "Regime-adaptive Meta pool — inspiration for head kill-shot / limb enable switching.",
        "addon_refs": ["https://stoic.ai/"],
        "fit": "inspiration",
    },
    "bitsgap_dca_combo": {
        "name": "Bitsgap DCA / COMBO",
        "source": "Bitsgap",
        "style": "dca",
        "category": "momentum",
        "limbs": [],
        "when": "directional averaging — not our spatial body",
        "notes": "Skip for arb body; useful only if we add a directional farm limb.",
        "addon_refs": ["https://bitsgap.com/"],
        "fit": "low",
    },
    "factor_residual_stat_arb": {
        "name": "Factor-residual statistical arb",
        "source": "Trading Strategy / Avellaneda-Lee literature",
        "style": "stat_arb",
        "category": "arbitrage",
        "limbs": ["pbook", "executor"],
        "when": "cross-sectional residual s-score",
        "notes": "Crypto caveat: strip PC1 (BTC mode) first. Our cutting_edge is the micro version of residual filtering.",
        "addon_refs": [
            "https://github.com/tradingstrategy-ai/docs",
            "https://stratcraft.ai/algorithms",
        ],
        "fit": "medium",
    },
    "datamaxi_cex_spread": {
        "name": "CEX–CEX spread playbook",
        "source": "DataMaxi+",
        "style": "cex_cex_arb",
        "category": "arbitrage",
        "limbs": ["datamaxi", "hunter", "pbook"],
        "when": "capital constrained, low ops",
        "notes": "Installed as `datamaxi` limb — Premium API when keyed, else local BN↔NK playbook gates.",
        "addon_refs": ["https://docs.datamaxiplus.com/strategies/cex-cex-spread"],
        "fit": "installed",
    },
}


def list_profiles(
    *,
    fit: str | None = None,
    limb: str | None = None,
    category: str | None = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for pid, meta in PROFIT_TRADING_PROFILES.items():
        if limb and limb not in (meta.get("limbs") or []):
            continue
        if category and str(meta.get("category") or "") != category:
            continue
        if fit and fit not in (None, "any") and str(meta.get("fit") or "") != fit:
            continue
        rows.append({"id": pid, **meta})
    return rows


def profiles_for_limb(limb: str) -> List[Dict[str, Any]]:
    return list_profiles(limb=limb)


def profiles_by_category(category: str) -> List[Dict[str, Any]]:
    return list_profiles(category=category)


def strategy_catalog() -> Dict[str, Any]:
    """Four families + installed profiles under each."""
    cats = list_categories()
    out = []
    for cat in cats:
        cid = cat["id"]
        out.append({
            **cat,
            "profiles": list_profiles(category=cid),
            "installed_profiles": list_profiles(category=cid, fit="installed"),
        })
    return {
        "categories": out,
        "category_ids": list(STRATEGY_CATEGORIES.keys()),
    }


def actionable_addons() -> List[Dict[str, Any]]:
    """Profiles worth looking through for next profit-maker work."""
    want = {"high", "medium", "inspiration", "browse", "already_present", "installed"}
    return [
        {"id": pid, **meta}
        for pid, meta in PROFIT_TRADING_PROFILES.items()
        if meta.get("fit") in want or meta.get("fit") is None
    ]
