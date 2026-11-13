"""Tighten limb enrichment with the four strategy categories.

Attaches arbitrage / momentum / VWAP / grid context onto deals and limb
snapshots so pbook, hunter, and head share one categorized view.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.config.profit_strategy_categories import (
    STRATEGY_CATEGORIES,
    category_for_limb,
    limb_category_map,
    list_categories,
)
from backend.services import crypto_exchange_service as ex


def _sym_usdt(symbol: Any) -> str:
    s = str(symbol or "").upper().replace("/", "").replace("-", "").replace("_", "")
    if not s:
        return ""
    if s.endswith("USDT") or s.endswith("USDC"):
        return s if s.endswith("USDT") else s[:-4] + "USDT"
    return s + "USDT"


def enrich_deal(deal: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``deal`` with ``strategy`` enrichment block."""
    row = dict(deal or {})
    sym = _sym_usdt(row.get("symbol"))
    categories: List[str] = ["arbitrage"]  # spatial deals always sit in arb family

    momentum_hint = None
    vwap_hint = None
    try:
        from backend.services.exchange_momentum_arm_service import latest_momentum_hint
        momentum_hint = latest_momentum_hint(sym) if sym else latest_momentum_hint()
    except Exception:
        momentum_hint = None
    try:
        from backend.services.exchange_vwap_arm_service import latest_vwap_hint
        vwap_hint = latest_vwap_hint(sym) if sym else latest_vwap_hint()
    except Exception:
        vwap_hint = None

    mom_block = None
    if isinstance(momentum_hint, dict) and momentum_hint.get("ok"):
        mom_block = {
            "score": momentum_hint.get("momentum_score"),
            "return_bps": momentum_hint.get("return_bps"),
            "volume_ratio": momentum_hint.get("volume_ratio"),
            "stop_pct": momentum_hint.get("stop_pct"),
            "stop_price": momentum_hint.get("stop_price"),
            "bias": momentum_hint.get("bias"),
            "actionable": bool(momentum_hint.get("actionable")),
        }
        categories.append("momentum")

    vwap_block = None
    if isinstance(vwap_hint, dict) and vwap_hint.get("ok"):
        vwap_block = {
            "vwap": vwap_hint.get("vwap"),
            "distance_bps": vwap_hint.get("distance_bps"),
            "session_bias": vwap_hint.get("session_bias"),
            "bands": vwap_hint.get("bands"),
            "support": vwap_hint.get("support"),
            "resistance": vwap_hint.get("resistance"),
        }
        categories.append("vwap")

    # Grid context is venue-agnostic thin-quote / open-order pulse when present.
    grid_block = None
    try:
        grid_state = ex._read_json(os.path.join(ex._DATA_DIR, "grid_bot_state.json"), {})
        if isinstance(grid_state, dict) and grid_state:
            grid_block = {
                "open_orders": grid_state.get("open_orders") or grid_state.get("orders"),
                "realized": grid_state.get("realized") or grid_state.get("realized_pnl"),
                "thin_quote": grid_state.get("thin_quote"),
            }
            categories.append("grid")
    except Exception:
        grid_block = None

    # Align VWAP/momentum bias with arb route when possible.
    align = "neutral"
    route_buy = str(row.get("buy_venue") or "")
    if mom_block and mom_block.get("bias") == "long_burst" and float(row.get("net_bps") or 0) > 0:
        align = "momentum_confirms_arb_long"
    if vwap_block:
        bias = str(vwap_block.get("session_bias") or "")
        if bias == "buy_below_vwap":
            align = "vwap_supports_buy_leg" if align == "neutral" else align + "+vwap_buy"
        elif bias == "sell_above_vwap":
            align = "vwap_supports_sell_leg" if align == "neutral" else align + "+vwap_sell"

    row["strategy"] = {
        "categories": sorted(set(categories)),
        "primary": "arbitrage",
        "alignment": align,
        "momentum": mom_block,
        "vwap": vwap_block,
        "grid": grid_block,
        "catalog": {cid: STRATEGY_CATEGORIES[cid]["name"] for cid in sorted(set(categories)) if cid in STRATEGY_CATEGORIES},
    }
    # Keep flat keys for quick ledger / technique filters.
    if mom_block:
        row["momentum_score"] = mom_block.get("score")
        row["momentum_stop_pct"] = mom_block.get("stop_pct")
    if vwap_block:
        row["vwap"] = vwap_block.get("vwap")
        row["vwap_distance_bps"] = vwap_block.get("distance_bps")
        row["vwap_bias"] = vwap_block.get("session_bias")
    _ = route_buy  # reserved for future route-aware VWAP venue pick
    return row


def enrich_hitlist(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [enrich_deal(r) for r in (rows or [])]


def limb_enrichment_snapshot() -> Dict[str, Any]:
    """Head / ops: category map + latest hints for all four families."""
    mom = None
    vwap = None
    try:
        from backend.services.exchange_momentum_arm_service import momentum_status
        mom = (momentum_status().get("state") or {}).get("momentum_hint")
    except Exception:
        mom = None
    try:
        from backend.services.exchange_vwap_arm_service import vwap_status
        vwap = (vwap_status().get("state") or {}).get("vwap_hint")
    except Exception:
        vwap = None
    return {
        "categories": list_categories(),
        "limb_to_category": limb_category_map(),
        "hints": {
            "momentum": mom,
            "vwap": vwap,
        },
        "by_limb": {
            limb: (category_for_limb(limb) or {}).get("id")
            for limb in limb_category_map()
        },
    }
