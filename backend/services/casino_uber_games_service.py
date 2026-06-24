"""Uber games — premium real-currency casino tier + MN2 network bonuses."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "casino_uber_games.json")


def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_uber_catalog(*, venue: Optional[str] = None) -> Dict[str, Any]:
    cfg = _load_config()
    games = [dict(g) for g in (cfg.get("games") or []) if isinstance(g, dict)]
    venues = cfg.get("discord_venues") or []
    if venue:
        venues = [v for v in venues if v.get("id") == venue or venue in (v.get("id") or "")]
    return {
        "success": True,
        "preferred_currencies": cfg.get("preferred_currency_order") or ["usd", "mn2"],
        "games": games,
        "venues": venues,
        "network_bonus": cfg.get("network_bonus") or {},
    }


def _game_row(game_id: str) -> Optional[Dict[str, Any]]:
    return next((g for g in (_load_config().get("games") or []) if g.get("id") == game_id), None)


def _validate_uber_bet(game: Dict[str, Any], bet: float, currency: str) -> Optional[str]:
    currency = (currency or "usd").lower()
    if currency == "usd":
        lo, hi = float(game.get("min_bet_usd") or 1), float(game.get("max_bet_usd") or 500)
    elif currency == "mn2":
        lo, hi = float(game.get("min_bet_mn2") or 0.01), float(game.get("max_bet_mn2") or 50)
    else:
        return "uber_requires_usd_or_mn2"
    if bet < lo or bet > hi:
        return f"bet_out_of_range_{lo}_{hi}"
    return None


def play_uber(
    user_id: str,
    game_id: str,
    bet: float,
    currency: str,
    **play_kwargs: Any,
) -> Dict[str, Any]:
    """Delegate to core casino engine; apply network bonus on wins."""
    uid = (user_id or "").strip()
    game = _game_row(game_id)
    if not game:
        return {"success": False, "error": "unknown_uber_game"}
    currency = (currency or "usd").lower()
    err = _validate_uber_bet(game, float(bet), currency)
    if err:
        return {"success": False, "error": err}
    engine = (game.get("engine") or "").strip()
    try:
        from backend.services import casino_service
        if engine == "crash":
            auto = play_kwargs.get("auto_cashout")
            out = casino_service.start_crash_round(uid, float(bet), currency=currency, auto_cashout=auto)
        elif engine == "plinko":
            risk = play_kwargs.get("risk") or game.get("risk_default") or "high"
            out = casino_service.play_plinko(uid, float(bet), currency=currency, risk=risk)
        elif engine == "wheel":
            risk = play_kwargs.get("risk") or game.get("risk_default") or "high"
            out = casino_service.play_wheel(uid, float(bet), currency=currency, risk=risk)
        elif engine == "keno":
            picks = play_kwargs.get("picks") or play_kwargs.get("spots") or [1, 2, 3, 4]
            if isinstance(picks, int):
                picks = list(range(1, picks + 1))
            out = casino_service.play_keno(uid, float(bet), picks, currency=currency)
        elif engine == "mines":
            out = casino_service.start_mines_round(
                uid, float(bet), currency=currency, mines=int(play_kwargs.get("mines") or 5),
            )
        else:
            return {"success": False, "error": "engine_not_supported"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    if out.get("success") and float(out.get("net") or 0) > 0:
        try:
            from backend.services.casino_network_rewards_service import apply_uber_win_bonus
            bonus = apply_uber_win_bonus(
                uid, currency=currency, net=float(out.get("net") or 0),
                mult=float(game.get("network_bonus_mult") or 1.0),
            )
            if bonus.get("mn2_bonus"):
                out["network_bonus_mn2"] = bonus.get("mn2_bonus")
        except Exception:
            pass
    out["uber_game_id"] = game_id
    out["uber_tier"] = True
    return out
