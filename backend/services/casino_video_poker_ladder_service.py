"""
Video poker ladder — daily escalating cosmetic pay tables by rank or XP.

Payouts use the base paytable (published RTP). Tier paytables are display-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _config() -> Dict[str, Any]:
    try:
        from backend.services.casino_service import _load_config

        ladder = _load_config().get("video_poker_ladder") or {}
        return ladder if isinstance(ladder, dict) else {}
    except Exception:
        return {}


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _user_xp(user_id: str) -> float:
    try:
        from backend.services.casino_progression import get_profile

        prof = get_profile(user_id)
        xp_block = prof.get("xp") or {}
        return float(xp_block.get("xp") or 0)
    except Exception:
        return 0.0


def _user_daily_rank(user_id: str, currency: str = "coins") -> Optional[int]:
    try:
        from backend.services.casino_service import get_leaderboard

        board = get_leaderboard(period="today", limit=500, currency=currency)
        for row in board.get("leaderboard") or []:
            if row.get("user_id") == user_id:
                rank = int(row.get("rank") or 0)
                return rank if rank > 0 else None
    except Exception:
        pass
    return None


def _sorted_tiers(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [t for t in (cfg.get("tiers") or []) if isinstance(t, dict)]


def _resolve_tier(
    user_id: str, cfg: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Dict[str, Any]]:
    rank_by = str(cfg.get("rank_by") or "daily_rank").lower()
    tiers = _sorted_tiers(cfg)
    if not tiers:
        return None, None, {"mode": rank_by, "daily_rank": None, "xp": 0.0}

    if rank_by == "xp":
        xp = _user_xp(user_id)
        ordered = sorted(tiers, key=lambda t: float(t.get("min_xp") or 0), reverse=True)
        current = next((t for t in ordered if xp >= float(t.get("min_xp") or 0)), ordered[-1])
        cur_min = float(current.get("min_xp") or 0)
        higher = sorted(
            [t for t in tiers if float(t.get("min_xp") or 0) > cur_min],
            key=lambda t: float(t.get("min_xp") or 0),
        )
        nxt = higher[0] if higher else None
        return current, nxt, {"mode": "xp", "daily_rank": None, "xp": round(xp, 2)}

    rank = _user_daily_rank(user_id)
    current = None
    for tier in sorted(tiers, key=lambda t: int(t.get("min_rank") or 999)):
        min_r = int(tier.get("min_rank") or 1)
        max_r = int(tier.get("max_rank") or min_r)
        if rank is not None and min_r <= rank <= max_r:
            current = tier
            break
    if current is None:
        defaults = [t for t in tiers if t.get("default")]
        current = defaults[0] if defaults else max(tiers, key=lambda t: int(t.get("max_rank") or 0))

    nxt = None
    if current is not None:
        cur_min = int(current.get("min_rank") or 999)
        better = [t for t in tiers if int(t.get("min_rank") or 999) < cur_min]
        if better:
            nxt = min(better, key=lambda t: int(t.get("min_rank") or 999))

    return current, nxt, {
        "mode": "daily_rank",
        "daily_rank": rank,
        "xp": round(_user_xp(user_id), 2),
    }


def tier_paytable(base: Dict[str, float], tier: Optional[Dict[str, Any]]) -> Dict[str, float]:
    if not tier:
        return dict(base)
    override = tier.get("paytable")
    if isinstance(override, dict) and override:
        merged = dict(base)
        merged.update({k: float(v) for k, v in override.items()})
        return merged
    boost = float(tier.get("paytable_boost") or 1.0)
    if boost == 1.0:
        return dict(base)
    return {k: round(float(v) * boost, 4) for k, v in base.items()}


def _tier_payload(
    tier: Optional[Dict[str, Any]], base_paytable: Dict[str, float]
) -> Optional[Dict[str, Any]]:
    if not tier:
        return None
    pt = tier_paytable(base_paytable, tier)
    return {
        "tier_id": tier.get("tier_id") or tier.get("id") or "tier",
        "label": tier.get("label") or "Tier",
        "min_rank": tier.get("min_rank"),
        "max_rank": tier.get("max_rank"),
        "min_xp": tier.get("min_xp"),
        "paytable_boost": tier.get("paytable_boost"),
        "paytable": pt,
    }


def get_ladder_status(user_id: str) -> Dict[str, Any]:
    cfg = _config()
    if not cfg.get("enabled", True):
        return {"success": True, "enabled": False}

    base_pt: Dict[str, float] = {}
    try:
        from backend.services.casino_service import _video_poker_config

        base_pt = _video_poker_config().get("paytable") or {}
    except Exception:
        pass

    current, nxt, meta = _resolve_tier(user_id, cfg)
    return {
        "success": True,
        "enabled": True,
        "date": _today_key(),
        "rank_by": cfg.get("rank_by") or "daily_rank",
        "rtp_published": float(cfg.get("rtp_published") or 99.5),
        "current_tier": _tier_payload(current, base_pt),
        "next_tier": _tier_payload(nxt, base_pt),
        **meta,
        "note": "Cosmetic pay table tier only — payouts maintain published RTP band.",
    }


def apply_ladder_on_draw(
    user_id: str,
    final_hand: Sequence[int],
    base_paytable: Dict[str, float],
) -> Dict[str, Any]:
    """Evaluate hand: base multiplier for payout, tier multiplier for display."""
    from backend.services.engines import cards as cards_engine

    cfg = _config()
    current, _, meta = _resolve_tier(user_id, cfg)
    tier_pt = tier_paytable(base_paytable, current)
    base_name, base_mult = cards_engine.evaluate_video_poker(final_hand, base_paytable)
    disp_name, disp_mult = cards_engine.evaluate_video_poker(final_hand, tier_pt)
    return {
        "payout_multiplier": base_mult,
        "display_multiplier": disp_mult,
        "hand_name": base_name,
        "display_hand_name": disp_name,
        "tier_id": (current or {}).get("tier_id") or "base",
        "tier_label": (current or {}).get("label") or "Base table",
        "cosmetic_paytable": tier_pt,
        "ladder": meta,
    }
