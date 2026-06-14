"""
Wheel of Fortune engine (pure).

A wheel is a list of weighted segments, each with a payout multiplier. A single
provably-fair float selects the landing segment proportional to its weight, so
one RNG draw determines (and verifies) the spin. Return-to-player is the
weight-averaged multiplier. All functions are side-effect free.
"""
from __future__ import annotations

from typing import Dict, List


def _total_weight(segments: List[Dict]) -> float:
    return sum(float(s.get("weight", 1)) for s in segments) or 1.0


def spin(rand_float: float, segments: List[Dict]) -> Dict[str, object]:
    """Pick a landing segment by weight from a float in [0, 1)."""
    total = _total_weight(segments)
    target = min(max(float(rand_float), 0.0), 0.999999999) * total
    acc = 0.0
    for idx, seg in enumerate(segments):
        acc += float(seg.get("weight", 1))
        if target < acc:
            return {"index": idx, "multiplier": float(seg.get("multiplier", 0))}
    last = len(segments) - 1
    return {"index": last, "multiplier": float(segments[last].get("multiplier", 0))}


def rtp(segments: List[Dict]) -> float:
    """Weight-averaged multiplier (= return-to-player)."""
    total = _total_weight(segments)
    return sum(float(s.get("multiplier", 0)) * float(s.get("weight", 1)) for s in segments) / total
