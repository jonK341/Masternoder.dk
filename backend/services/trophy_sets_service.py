"""Trophy set badges — genesis, million club, round numbers."""
from __future__ import annotations

from typing import Any, Dict, List


def edition_set_badges(edition: Dict[str, Any]) -> List[str]:
    badges: List[str] = []
    height = edition.get("block_height")
    if height is not None:
        h = int(height)
        if 1 <= h <= 1000:
            badges.append("Genesis Set (1–1000)")
        if h == 1_000_000:
            badges.append("Million Club")
        if h > 0 and h % 10000 == 0:
            badges.append(f"Round Block #{h}")
        if h == 1:
            badges.append("First Block")
    via = (edition.get("acquired_via") or "").strip()
    if via == "staking_winner":
        badges.append("Interval Champion")
    return badges
