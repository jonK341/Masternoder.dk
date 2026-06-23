"""
Keno engine (pure).

The house draws `draw` distinct numbers from a pool of `1..pool`. The player
picks up to `max_spots` numbers; the payout multiplier depends on how many of
their spots were hit, via a per-spots-count pay table.

The draw is derived deterministically from a single provably-fair float (seeded
partial Fisher-Yates), so it is fully verifiable from server_seed + client_seed
+ nonce. `rtp()` computes the exact return-to-player using the hypergeometric
distribution, so pay tables can be calibrated precisely. Side-effect free.
"""
from __future__ import annotations

from math import comb
from typing import Dict, List

_MASK64 = (1 << 64) - 1


def _lcg_stream(seed: int):
    state = seed & _MASK64
    if state == 0:
        state = 0x9E3779B97F4A7C15
    while True:
        state = (state * 6364136223846793005 + 1442695040888963407) & _MASK64
        yield (state >> 16) / float(1 << 48)


def draw_numbers(rand_float: float, pool: int, draw: int) -> List[int]:
    """Deterministic, verifiable set of `draw` distinct numbers from 1..pool."""
    n = int(pool)
    d = max(0, min(int(draw), n))
    seed = int(min(max(float(rand_float), 0.0), 0.999999999) * (1 << 52))
    gen = _lcg_stream(seed)
    idx = list(range(1, n + 1))
    for i in range(d):
        r = next(gen)
        j = i + int(r * (n - i))
        if j >= n:
            j = n - 1
        idx[i], idx[j] = idx[j], idx[i]
    return sorted(idx[:d])


def count_hits(spots: List[int], drawn: List[int]) -> int:
    return len(set(int(s) for s in spots) & set(int(d) for d in drawn))


def payout_multiplier(spots_count: int, hits: int, pay_table: Dict) -> float:
    """Look up the total-return multiplier for (spots picked, hits matched)."""
    row = pay_table.get(str(int(spots_count))) if isinstance(pay_table, dict) else None
    if not isinstance(row, dict):
        return 0.0
    return float(row.get(str(int(hits)), 0.0) or 0.0)


def hyper_prob(spots_count: int, hits: int, pool: int, draw: int) -> float:
    """P(exactly `hits` of `spots_count` picks are among `draw` drawn from pool)."""
    s = int(spots_count)
    k = int(hits)
    n = int(pool)
    d = int(draw)
    if k > s or k > d or (s - k) > (n - d):
        return 0.0
    return comb(s, k) * comb(n - s, d - k) / comb(n, d)


def rtp(spots_count: int, pay_table: Dict, pool: int, draw: int) -> float:
    """Exact return-to-player for picking `spots_count` numbers."""
    total = 0.0
    for k in range(0, int(spots_count) + 1):
        total += hyper_prob(spots_count, k, pool, draw) * payout_multiplier(spots_count, k, pay_table)
    return total
