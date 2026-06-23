"""
Mines engine (pure).

A grid of `tiles` cells hides `mines` bombs. The player reveals safe cells one
at a time; each safe reveal raises the multiplier. Revealing a bomb loses the
stake. Cash out any time for bet * multiplier(revealed).

The bomb layout is derived deterministically from a single provably-fair float
(seeded Fisher-Yates), so the whole board is committed at round start and can be
recomputed from server_seed + client_seed + nonce. The multiplier is the fair
inverse-probability curve scaled by (1 - house_edge):

    multiplier(k) = (1 - house_edge) * Π_{i=0}^{k-1} (N - i) / (N - m - i)

All functions are side-effect free.
"""
from __future__ import annotations

from typing import List

_MASK64 = (1 << 64) - 1


def _lcg_stream(seed: int):
    """Deterministic 64-bit LCG yielding floats in [0, 1)."""
    state = seed & _MASK64
    if state == 0:
        state = 0x9E3779B97F4A7C15
    while True:
        state = (state * 6364136223846793005 + 1442695040888963407) & _MASK64
        yield (state >> 16) / float(1 << 48)


def mine_positions(rand_float: float, tiles: int, mines: int) -> List[int]:
    """Deterministic, verifiable bomb indices from one provably-fair float."""
    n = int(tiles)
    m = max(0, min(int(mines), n - 1))
    seed = int(min(max(float(rand_float), 0.0), 0.999999999) * (1 << 52))
    gen = _lcg_stream(seed)
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        r = next(gen)
        j = int(r * (i + 1))
        if j > i:
            j = i
        idx[i], idx[j] = idx[j], idx[i]
    return sorted(idx[:m])


def multiplier(tiles: int, mines: int, revealed_count: int, house_edge: float = 0.01) -> float:
    """Fair cash-out multiplier after `revealed_count` safe reveals."""
    n = int(tiles)
    m = int(mines)
    k = int(revealed_count)
    if k <= 0:
        return 1.0
    edge = min(max(float(house_edge), 0.0), 0.99)
    prod = 1.0
    for i in range(k):
        denom = (n - m - i)
        if denom <= 0:
            break
        prod *= (n - i) / denom
    return round((1.0 - edge) * prod, 4)


def safe_tiles(tiles: int, mines: int) -> int:
    return max(0, int(tiles) - int(mines))
