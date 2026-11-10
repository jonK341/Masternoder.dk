"""Inventory skew for ladder entry prices (Avellaneda–Stoikov style).

When base inventory (USD) exceeds quote inventory, sells move closer to mid and
buys move farther — so the book leans into unloading the heavy side. The reverse
holds when quote-rich. ``skew`` is clipped to ``[-1, 1]``.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping


def inventory_usd(balances: Mapping[str, float], symbol: str, mid: float, quote: str) -> Dict[str, float]:
    base = float(balances.get(symbol) or 0.0) * float(mid)
    q = float(balances.get(quote) or 0.0)
    return {"base_usd": base, "quote_usd": q, "total_usd": base + q}


def skew_factor(balances: Mapping[str, float], symbol: str, mid: float, quote: str) -> float:
    """+1 = fully long base, -1 = fully long quote, 0 = balanced or empty."""
    parts = inventory_usd(balances, symbol, mid, quote)
    total = parts["total_usd"]
    if total <= 1e-9:
        return 0.0
    raw = (parts["base_usd"] - parts["quote_usd"]) / total
    return max(-1.0, min(1.0, raw))


def skewed_entry_offset_bps(
    side: str,
    level: int,
    cfg: Mapping[str, Any],
    *,
    skew: float,
) -> float:
    """Entry distance in bps after inventory skew.

    Positive ``skew`` (long base) pulls sells in and pushes buys out by up to
    ``inventory_skew_bps``.
    """
    base = float(cfg["first_bps"]) + int(level) * float(cfg["step_bps"])
    strength = float(cfg.get("inventory_skew_bps") or 0.0)
    if strength <= 0 or abs(skew) < 1e-9:
        return base
    # sell closer when long base (skew>0); buy closer when long quote (skew<0)
    if side == "sell":
        return max(1.0, base - strength * skew)
    return max(1.0, base + strength * skew)


def apply_skew_to_cfg(cfg: Dict[str, Any], *, skew: float) -> Dict[str, Any]:
    """Return a shallow copy; callers still pass level into ``skewed_entry_offset_bps``."""
    out = dict(cfg)
    out["_inventory_skew"] = float(skew)
    return out
