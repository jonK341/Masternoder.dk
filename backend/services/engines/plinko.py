"""
Plinko engine (pure).

A ball drops through `rows` peg rows; at each peg it goes left or right with
probability 1/2. The landing bin equals the number of right moves, so bins
follow a binomial(rows, 1/2) distribution. The payout multiplier is read from
a per-risk table of length `rows + 1`.

The whole drop path is derived from a single provably-fair float via its binary
expansion, so one RNG draw fully determines (and lets a player verify) the
outcome. All functions are side-effect free.
"""
from __future__ import annotations

from math import comb
from typing import Dict, List


def drop_path(rand_float: float, rows: int) -> List[int]:
    """Binary-expand a float in [0, 1) into `rows` fair left(0)/right(1) bits."""
    x = min(max(float(rand_float), 0.0), 0.999999999)
    bits: List[int] = []
    for _ in range(int(rows)):
        x *= 2.0
        bit = int(x)
        if bit > 1:
            bit = 1
        bits.append(bit)
        x -= bit
    return bits


def play(rand_float: float, rows: int, table: List[float]) -> Dict[str, object]:
    """Resolve a drop: returns landing bin, L/R path, and payout multiplier."""
    bits = drop_path(rand_float, rows)
    final_bin = sum(bits)
    final_bin = max(0, min(final_bin, len(table) - 1))
    multiplier = float(table[final_bin])
    return {
        "bin": final_bin,
        "path": ["R" if b else "L" for b in bits],
        "multiplier": multiplier,
    }


def rtp(rows: int, table: List[float]) -> float:
    """Exact return-to-player for a risk table over a binomial(rows, 1/2) board."""
    rows = int(rows)
    total = float(2 ** rows)
    return sum(comb(rows, k) * float(table[k]) for k in range(rows + 1)) / total
