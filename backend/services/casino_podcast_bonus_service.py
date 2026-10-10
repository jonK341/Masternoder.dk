"""Podcast portal tie-in — bonus coins during live tournament windows (Wave 4)."""
from __future__ import annotations

from typing import Any, Dict, Optional


def _config() -> Dict[str, Any]:
    try:
        from backend.services.casino_service import _load_config
        block = (_load_config().get("podcast_tournament_bonus") or {})
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def _live_tournament_window() -> bool:
    try:
        from backend.services import casino_tournaments
        out = casino_tournaments.list_tournaments()
        for t in out.get("tournaments") or []:
            if isinstance(t, dict) and t.get("status") == "running":
                return True
    except Exception:
        pass
    return False


def maybe_award_podcast_bonus(
    user_id: str,
    *,
    podcast_active: bool = False,
    currency: str = "coins",
) -> Optional[Dict[str, Any]]:
    """Credit bonus coins when podcast strip is active during a live tournament."""
    cfg = _config()
    if not cfg.get("enabled", True):
        return None
    if not podcast_active:
        return None
    if not _live_tournament_window():
        return None
    bonus = float(cfg.get("bonus_coins_per_bet") or 5)
    if bonus <= 0:
        return None
    award_currency = "coins"
    if currency != "coins" and not cfg.get("coins_only", True):
        award_currency = currency
    try:
        from backend.services.casino_service import _apply_balance_delta, _round_payout
        amount = _round_payout(bonus, award_currency)
        _apply_balance_delta(
            user_id,
            amount,
            award_currency,
            "podcast_bonus",
            {"phase": "tournament_window", "podcast_active": True},
        )
    except Exception:
        return None
    return {"bonus": amount, "currency": award_currency, "reason": "podcast_tournament_window"}


def get_status(*, podcast_active: bool = False) -> Dict[str, Any]:
    cfg = _config()
    live = _live_tournament_window()
    eligible = bool(cfg.get("enabled", True) and podcast_active and live)
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "live_tournament": live,
        "podcast_active": bool(podcast_active),
        "eligible": eligible,
        "bonus_coins_per_bet": float(cfg.get("bonus_coins_per_bet") or 5),
    }
