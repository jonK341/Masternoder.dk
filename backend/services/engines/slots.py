"""
Slot engine (pure).

Evaluates reel outcomes for 3-reel (and N-reel) slots with optional wilds,
scatters, and simple paylines. casino_service orchestrates bet validation and
balance updates; this module only computes payouts.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple


def pick_symbol(symbols: Sequence[str], weights: Optional[Dict[str, float]], rand_float: float) -> str:
    pool = list(symbols)
    if weights:
        wts = [float(weights.get(s) or 1) for s in pool]
        total = sum(wts) or 1.0
        r = min(max(float(rand_float), 0.0), 0.999999999) * total
        acc = 0.0
        for sym, wt in zip(pool, wts):
            acc += wt
            if r <= acc:
                return sym
    idx = int(min(max(float(rand_float), 0.0), 0.999999999) * len(pool))
    return pool[min(idx, len(pool) - 1)]


def spin_reels(
    reel_count: int,
    symbols: Sequence[str],
    weights: Optional[Dict[str, float]],
    rand_floats: Sequence[float],
) -> List[str]:
    n = max(1, int(reel_count))
    floats = list(rand_floats)
    while len(floats) < n:
        floats.append(floats[-1] if floats else 0.5)
    return [pick_symbol(symbols, weights, floats[i]) for i in range(n)]


def _resolve_wild(reels: List[str], wild_symbols: Sequence[str]) -> List[str]:
    wilds = set(wild_symbols or [])
    if not wilds:
        return list(reels)
    resolved = list(reels)
    anchor = next((r for r in reels if r not in wilds), None)
    if anchor is None:
        return resolved
    for i, sym in enumerate(resolved):
        if sym in wilds:
            resolved[i] = anchor
    return resolved


def evaluate_line(
    reels: List[str],
    paytable: dict,
    *,
    wild_symbols: Optional[Sequence[str]] = None,
) -> Tuple[Optional[str], float, dict]:
    """Evaluate the primary payline (all reels must match for N-reel win)."""
    resolved = _resolve_wild(reels, wild_symbols or [])
    n = len(resolved)
    details_base = {"reels": reels, "resolved_reels": resolved, "near_miss": False}

    if n >= 3:
        symbol = resolved[0]
        if all(r == symbol for r in resolved):
            key = "five" if n >= 5 else ("four" if n >= 4 else "three")
            mult = float(
                (paytable.get(key) or {}).get(symbol)
                or paytable.get(f"default_{key}")
                or paytable.get("default_three")
                or 5.0
            )
            return symbol, mult, {
                **details_base,
                "match": key,
                "symbol": symbol,
                "multiplier": mult,
                "win_positions": list(range(n)),
            }

    if n == 3:
        pair = None
        pair_pos = None
        if resolved[0] == resolved[1]:
            pair, pair_pos = resolved[0], "left"
        elif resolved[1] == resolved[2]:
            pair, pair_pos = resolved[1], "right"
        elif resolved[0] == resolved[2]:
            pair, pair_pos = resolved[0], "outer"
        if pair:
            mult = float((paytable.get("two") or {}).get(pair) or paytable.get("default_two") or 1.2)
            win_pos = [0, 1] if pair_pos == "left" else ([1, 2] if pair_pos == "right" else [0, 2])
            return pair, mult, {
                **details_base,
                "match": "two",
                "symbol": pair,
                "multiplier": mult,
                "win_positions": win_pos,
            }
        wilds = set(wild_symbols or [])
        base = [r for r in reels if r not in wilds]
        if len(set(base)) == 2 and len(base) >= 2:
            details_base["near_miss"] = True

    return None, 0.0, {**details_base, "match": "none", "symbol": None, "multiplier": 0, "win_positions": []}


def scatter_bonus(
    reels: Sequence[str],
    scatter_symbol: Optional[str],
    scatter_min: int,
    scatter_multiplier: float,
) -> Tuple[int, float]:
    if not scatter_symbol:
        return 0, 0.0
    count = sum(1 for r in reels if r == scatter_symbol)
    if count < int(scatter_min or 3):
        return 0, 0.0
    return count, float(scatter_multiplier)
