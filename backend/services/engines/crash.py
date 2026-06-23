"""
Crash engine (pure).

A round picks a hidden bust multiplier from a provably-fair float, then a
rising multiplier curve grows over wall-clock time. The player cashes out
before the curve hits the bust point to win bet * cashout_multiplier.

The bust distribution uses the standard inverse-CDF crash formula so the
return-to-player equals (1 - house_edge) for *any* cash-out target:

    P(bust >= t) = (1 - house_edge) / t   for t >= 1
    EV(cash out at t) = P(reach t) * t = 1 - house_edge

All functions are side-effect free and deterministic given their inputs.
"""
from __future__ import annotations

import math

DEFAULT_HOUSE_EDGE = 0.03
# ln(2) / 5  → the curve reaches 2.00x at 5 seconds, 4.00x at 10s, etc.
DEFAULT_GROWTH_PER_SECOND = 0.13863


def crash_point(rand_float: float, house_edge: float = DEFAULT_HOUSE_EDGE) -> float:
    """Map a provably-fair float in [0, 1) to a bust multiplier (>= 1.00)."""
    r = min(max(float(rand_float), 0.0), 0.999999999)
    edge = min(max(float(house_edge), 0.0), 0.99)
    raw = (1.0 - edge) / (1.0 - r)
    bust = math.floor(raw * 100) / 100.0
    return max(1.0, bust)


def multiplier_at(elapsed_seconds: float, growth_per_second: float = DEFAULT_GROWTH_PER_SECOND) -> float:
    """The live multiplier shown after `elapsed_seconds`, floored to 2 decimals."""
    if elapsed_seconds is None or elapsed_seconds <= 0:
        return 1.0
    growth = float(growth_per_second) or DEFAULT_GROWTH_PER_SECOND
    value = math.exp(growth * float(elapsed_seconds))
    return max(1.0, math.floor(value * 100) / 100.0)


def seconds_for_multiplier(multiplier: float, growth_per_second: float = DEFAULT_GROWTH_PER_SECOND) -> float:
    """Inverse of multiplier_at: when the curve first reaches `multiplier`."""
    m = max(1.0, float(multiplier))
    growth = float(growth_per_second) or DEFAULT_GROWTH_PER_SECOND
    return math.log(m) / growth


def settle(
    *,
    bust: float,
    elapsed_seconds: float,
    requested_multiplier: float = None,
    auto_cashout: float = None,
    growth_per_second: float = DEFAULT_GROWTH_PER_SECOND,
) -> dict:
    """
    Decide the outcome of a cash-out attempt.

    - `bust` is the hidden bust multiplier for the round.
    - `elapsed_seconds` is server-measured time since the round started; it caps
      how high the player could possibly have cashed out (anti-cheat).
    - `requested_multiplier` is what the client claims it cashed out at; it is
      clamped to the server-computed reachable multiplier.
    - `auto_cashout`, if set and reached before bust, settles at that target.

    Returns {"won": bool, "cashout": float, "bust": float, "multiplier": float}
    where `multiplier` is the payout multiple (0.0 on a bust/loss).
    """
    reachable = multiplier_at(elapsed_seconds, growth_per_second)
    bust = max(1.0, float(bust))

    target = reachable
    if requested_multiplier is not None:
        try:
            req = float(requested_multiplier)
            if req > 0:
                target = min(target, req)
        except (TypeError, ValueError):
            pass
    if auto_cashout is not None:
        try:
            auto = float(auto_cashout)
            if auto >= 1.0 and auto <= reachable:
                target = min(target, auto)
        except (TypeError, ValueError):
            pass

    target = max(1.0, math.floor(target * 100) / 100.0)

    if target < bust:
        return {"won": True, "cashout": target, "bust": bust, "multiplier": target}
    return {"won": False, "cashout": 0.0, "bust": bust, "multiplier": 0.0}
