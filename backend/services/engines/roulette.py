"""
European roulette engine (pure).

A single provably-fair float selects a pocket in 0..36 (single zero). Bets are
evaluated to a **total-return** multiplier (stake included): a winning straight
pays 36× (the classic 35:1), even-money bets pay 2×, dozens/columns pay 3×, and
losers pay 0. The single green zero gives every standard bet the same house
edge — RTP = 36/37 ≈ 0.973 — which `rtp()` verifies. Side-effect free.
"""
from __future__ import annotations

from typing import Optional

POCKETS = 37  # 0..36, single zero (European)

RED = frozenset({1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36})

OUTSIDE_BETS = ("red", "black", "even", "odd", "low", "high", "dozen", "column")


def spin(rand_float: float, pockets: int = POCKETS) -> int:
    """Map a provably-fair float to a pocket in 0..pockets-1."""
    r = min(max(float(rand_float), 0.0), 0.999999999)
    return int(r * int(pockets))


def color(pocket: int) -> str:
    p = int(pocket)
    if p == 0:
        return "green"
    return "red" if p in RED else "black"


def evaluate(pocket: int, bet_type: str, selection: Optional[int] = None) -> float:
    """Total-return multiplier for one bet on a settled pocket (0 = lose)."""
    p = int(pocket)
    bt = (bet_type or "").strip().lower()

    if bt == "straight":
        try:
            sel = int(selection)
        except (TypeError, ValueError):
            return 0.0
        return 36.0 if p == sel else 0.0

    if p == 0:
        return 0.0  # zero loses all outside bets

    if bt == "red":
        return 2.0 if color(p) == "red" else 0.0
    if bt == "black":
        return 2.0 if color(p) == "black" else 0.0
    if bt == "even":
        return 2.0 if p % 2 == 0 else 0.0
    if bt == "odd":
        return 2.0 if p % 2 == 1 else 0.0
    if bt == "low":
        return 2.0 if 1 <= p <= 18 else 0.0
    if bt == "high":
        return 2.0 if 19 <= p <= 36 else 0.0
    if bt == "dozen":
        try:
            sel = int(selection)
        except (TypeError, ValueError):
            return 0.0
        lo = (sel - 1) * 12 + 1
        return 3.0 if sel in (1, 2, 3) and lo <= p <= lo + 11 else 0.0
    if bt == "column":
        try:
            sel = int(selection)
        except (TypeError, ValueError):
            return 0.0
        return 3.0 if sel in (1, 2, 3) and p % 3 == (sel % 3) else 0.0

    return 0.0


def evaluate_side_bet(pocket: int, side_type: str, hot_numbers: List[int], cold_numbers: List[int]) -> float:
    """Total-return multiplier for hot/cold side bet (8× published estimate)."""
    p = int(pocket)
    st = (side_type or "").strip().lower()
    if st == "hot":
        return 8.0 if p in hot_numbers else 0.0
    if st == "cold":
        return 8.0 if p in cold_numbers else 0.0
    return 0.0


def side_bet_rtp(side_type: str, hot_numbers: List[int], cold_numbers: List[int], pockets: int = POCKETS) -> float:
    n = int(pockets)
    return sum(
        evaluate_side_bet(p, side_type, hot_numbers, cold_numbers) for p in range(n)
    ) / n


def rtp(bet_type: str, selection: Optional[int] = None, pockets: int = POCKETS) -> float:
    """Exact return-to-player for a bet, averaged over every pocket."""
    n = int(pockets)
    return sum(evaluate(p, bet_type, selection) for p in range(n)) / n
