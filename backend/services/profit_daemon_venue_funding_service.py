"""Profit daemon — keep dual-venue arb legs funded (Binance quote + NonKYC inventory)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from scripts.daemon_env import daemon_mode_label, is_arbitrage_live


def venue_prefund_enabled() -> bool:
    raw = os.environ.get("PROFIT_DAEMON_VENUE_PREFUND", "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _hot_symbols_from_exchange_res(exchange_res: Dict[str, Any]) -> List[str]:
    plat = exchange_res.get("platform") if isinstance(exchange_res.get("platform"), dict) else {}
    ps = plat.get("profit_pair_search") if isinstance(plat.get("profit_pair_search"), dict) else {}
    hot = list(ps.get("hot_symbols") or [])
    if hot:
        return [str(s).upper() for s in hot if s]
    arb = plat.get("arbitrage") if isinstance(plat.get("arbitrage"), dict) else {}
    for action in arb.get("actions") or []:
        if not isinstance(action, dict):
            continue
        best = action.get("best") if isinstance(action.get("best"), dict) else {}
        sym = best.get("symbol") or best.get("pair")
        if sym:
            return [str(sym).upper()]
    return [str(os.environ.get("EXCHANGE_DUAL_FARM_SYMBOL", "DOGE")).upper()]


def maybe_ensure_dual_venue_funding(exchange_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prefund buy/sell legs for the live dual-venue farm agent when spreads are hot but unfunded.
    Uses rotation service (paper unless EXCHANGE_ROTATION_LIVE=1).
    """
    if not venue_prefund_enabled():
        return {"skipped": True, "reason": "disabled"}
    if not is_arbitrage_live() and daemon_mode_label() != "live":
        return {"skipped": True, "reason": "not_live_mode"}

    from backend.services.exchange_swap_rotation_service import rotation_live_enabled
    from backend.services.venue_funding_rotation_service import fund_venue_legs_for_symbol, rotation_agent_ids

    agent_ids = rotation_agent_ids()
    agent = (
        os.environ.get("EXCHANGE_DUAL_FARM_AGENT", "").strip()
        or (agent_ids[0] if agent_ids else "arb_live_dual_farm")
    )
    try:
        notional = float(os.environ.get("EXCHANGE_PAPER_TRADE_USD", "75") or 75)
    except (TypeError, ValueError):
        notional = 75.0
    dry_run = not rotation_live_enabled()
    symbols = _hot_symbols_from_exchange_res(exchange_res)[:3]
    outcomes: List[Dict[str, Any]] = []
    funded_any = False
    for sym in symbols:
        out = fund_venue_legs_for_symbol(
            agent,
            sym,
            notional,
            dry_run=dry_run,
            max_actions=3,
        )
        outcomes.append(out)
        if out.get("funded_ok") or out.get("already_funded"):
            funded_any = True
        elif out.get("success"):
            funded_any = True

    return {
        "success": True,
        "agent_id": agent,
        "symbols": symbols,
        "dry_run": dry_run,
        "funded_any": funded_any,
        "outcomes": outcomes,
    }
