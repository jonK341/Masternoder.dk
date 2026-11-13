"""Look-through catalog of profit-maker trading profiles.

Maps external / open-source strategy styles onto our profit-body limbs so we
can pick addons without guessing. Profiles are advisory — not auto-wired.
"""
from __future__ import annotations

from typing import Any, Dict, List

# Body limbs these profiles may attach to.
_LIMBS = ("hunter", "dual_farm", "courier", "latch", "closer", "executor", "pbook", "grid", "head")

PROFIT_TRADING_PROFILES: Dict[str, Dict[str, Any]] = {
    "precision_level_swing": {
        "name": "Precision level swing",
        "source": "classic floor pivots + swing H/L",
        "style": "swing_ta",
        "limbs": ["swing", "grid", "latch"],
        "when": "systematic TA with disciplined S/R / pivot entries",
        "notes": (
            "THIS is the repeatable swing system: trend bias from MA cross, "
            "entries at pivot S1/R1, stops beyond swing high/low — discipline + precision price levels."
        ),
        "fit": "installed",
    },
    "spatial_taker_cut": {
        "name": "Spatial taker (cutting edge)",
        "source": "internal",
        "style": "cex_cex_arb",
        "limbs": ["hunter", "executor", "pbook"],
        "when": "cutting_edge.band == fire",
        "notes": "Market buy cheap / sell rich only when cut_bps clears floor after skew−noise.",
    },
    "skew_maker_latch": {
        "name": "Skew maker latch",
        "source": "internal + Hummingbot maker ideas",
        "style": "passive_maker",
        "limbs": ["latch", "grid"],
        "when": "cutting_edge.band == latch",
        "notes": "Park limit sell on rich venue while mid-skew compresses; strike when fire.",
    },
    "quote_bridge_courier": {
        "name": "Quote-bridge courier",
        "source": "internal",
        "style": "inventory",
        "limbs": ["courier", "executor"],
        "when": "unfunded top route / thin buy-venue quote",
        "notes": "Raise USDC/USDT on buy venue via inventory sells — bridge without wire transfer.",
    },
    "grid_range_harvest": {
        "name": "Grid range harvest",
        "source": "Bitsgap GRID / Hummingbot pure MM",
        "style": "grid",
        "limbs": ["grid", "closer"],
        "when": "sideways book, quote funded",
        "notes": "Maker ladders; closer harvests dust. Pause on thin quote.",
        "addon_refs": ["https://bitsgap.com/", "https://hummingbot.org/"],
    },
    "hummingbot_spot_perp_basis": {
        "name": "Spot–perp basis / funding",
        "source": "Hummingbot spot_perpetual_arbitrage + DataMaxi funding",
        "style": "basis",
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
        "limbs": ["datamaxi", "hunter", "pbook"],
        "when": "capital constrained, low ops",
        "notes": "Installed as `datamaxi` limb — Premium API when keyed, else local BN↔NK playbook gates.",
        "addon_refs": ["https://docs.datamaxiplus.com/strategies/cex-cex-spread"],
        "fit": "installed",
    },
}


def list_profiles(*, fit: str | None = None, limb: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for pid, meta in PROFIT_TRADING_PROFILES.items():
        if limb and limb not in (meta.get("limbs") or []):
            continue
        if fit and fit not in (None, "any") and str(meta.get("fit") or "") != fit:
            continue
        rows.append({"id": pid, **meta})
    return rows


def profiles_for_limb(limb: str) -> List[Dict[str, Any]]:
    return list_profiles(limb=limb)


def actionable_addons() -> List[Dict[str, Any]]:
    """Profiles worth looking through for next profit-maker work."""
    want = {"high", "medium", "inspiration", "browse", "already_present", "installed"}
    return [
        {"id": pid, **meta}
        for pid, meta in PROFIT_TRADING_PROFILES.items()
        if meta.get("fit") in want or meta.get("fit") is None
    ]
