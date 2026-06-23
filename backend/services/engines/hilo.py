"""
Hi-Lo engine (pure).

A card with a rank in 1..`ranks` is shown. The player guesses whether the next
card will be **higher-or-equal** or **lower-or-equal**. Each correct guess
multiplies the running pot by a fair, house-edged multiplier derived from the
true probability of that outcome; one wrong guess loses everything. The player
can cash out the running pot at any time.

Cards are drawn uniformly with replacement (an "infinite shoe"), so each step's
probability depends only on the current card, which keeps the multipliers exact
and verifiable. Ties resolve in the player's favour for whichever side they
picked, so there is always a valid (and a safe) choice. Side-effect free.
"""
from __future__ import annotations

RANKS = 13


def card_from_float(rand_float: float, ranks: int = RANKS) -> int:
    """Map a provably-fair float to a card rank in 1..ranks."""
    r = min(max(float(rand_float), 0.0), 0.999999999)
    return 1 + int(r * int(ranks))


def prob_higher(card: int, ranks: int = RANKS) -> float:
    """P(next card >= card) drawing uniformly from 1..ranks."""
    n = int(ranks)
    return (n - int(card) + 1) / n


def prob_lower(card: int, ranks: int = RANKS) -> float:
    """P(next card <= card) drawing uniformly from 1..ranks."""
    return int(card) / int(ranks)


def win_probability(card: int, direction: str, ranks: int = RANKS) -> float:
    return prob_higher(card, ranks) if direction == "higher" else prob_lower(card, ranks)


def step_multiplier(card: int, direction: str, house_edge: float = 0.02, ranks: int = RANKS) -> float:
    """Fair per-step multiplier = (1 - house_edge) / P(win)."""
    p = win_probability(card, direction, ranks)
    if p <= 0:
        return 0.0
    edge = min(max(float(house_edge), 0.0), 0.99)
    return round((1.0 - edge) / p, 4)


def wins(card: int, next_card: int, direction: str) -> bool:
    if direction == "higher":
        return int(next_card) >= int(card)
    return int(next_card) <= int(card)
