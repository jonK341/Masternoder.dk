"""Premium features for cross-trading agents.

Premium agents get a base edge bonus, capture a share of the prediction engine's
edge uplift, scan more often (cycles multiplier), and unlock advanced skills.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

from backend.services import crypto_exchange_service as ex

_CONFIG_PATH = os.path.join(ex._BASE, "data", "exchange_premium_config.json")


def load_premium_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def premium_features() -> Dict[str, Any]:
    cfg = load_premium_config()
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "premium_base_bonus_bps": cfg.get("premium_base_bonus_bps", 12),
        "edge_uplift_share": cfg.get("edge_uplift_share", 0.6),
        "cycles_multiplier": cfg.get("cycles_multiplier", 1.5),
        "fee_discount_bps": cfg.get("fee_discount_bps", 5),
        "premium_skills": cfg.get("premium_skills", []),
        "features": cfg.get("premium_features", []),
    }


def is_premium_skill(skill_id: str) -> bool:
    return (skill_id or "") in (load_premium_config().get("premium_skills") or [])


def edge_bonus_and_cycles(is_premium: bool, *, market_uplift_bps: float = 0.0,
                          base_cycles_per_day: float = 24.0) -> Tuple[float, float]:
    """Return (edge_bonus_bps, effective_cycles_per_day) for an agent."""
    cfg = load_premium_config()
    if not is_premium or not cfg.get("enabled", True):
        return 0.0, float(base_cycles_per_day or 0)
    base_bonus = float(cfg.get("premium_base_bonus_bps") or 0)
    share = float(cfg.get("edge_uplift_share") or 0)
    bonus = round(base_bonus + share * max(0.0, float(market_uplift_bps or 0)), 2)
    cycles = float(base_cycles_per_day or 0) * float(cfg.get("cycles_multiplier") or 1.0)
    return bonus, round(cycles, 2)
