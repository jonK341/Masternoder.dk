"""
Casino math calculators — RTP, EV, Kelly sizing, per-game win probability hints.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_GUIDES_PATH = os.path.join(_ROOT, "data", "casino_game_guides.json")


def _load_guides() -> Dict[str, Any]:
    if not os.path.isfile(_GUIDES_PATH):
        return {"games": {}}
    try:
        with open(_GUIDES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"games": {}}
    except Exception:
        return {"games": {}}


def _game_cfg(game_id: str) -> Dict[str, Any]:
    from backend.services import casino_service as casino

    cfg = casino.get_public_config() or {}
    games = cfg.get("games") if isinstance(cfg.get("games"), dict) else {}
    row = games.get(game_id) if isinstance(games.get(game_id), dict) else {}
    return dict(row)


def win_probability_estimate(game_id: str, **params) -> Dict[str, Any]:
    """Heuristic win chance (not live RNG outcome)."""
    g = _game_cfg(game_id)
    gid = (game_id or "").strip().lower()

    if gid == "coin_flip":
        p = 0.5
    elif gid == "dice":
        p = 1.0 / max(int(g.get("sides") or 6), 1)
    elif gid == "rps_bet" or gid == "rps_distribution" or gid == "rps_counter_pick":
        p = 1.0 / 3.0
    elif gid == "scratch_card":
        p = 0.35
    elif gid == "battle_outcome":
        pred = (params.get("prediction") or "win").strip().lower()
        dist = params.get("distribution") if isinstance(params.get("distribution"), dict) else {}
        p = float(dist.get(pred, 0) or 0) / 100.0 if dist else 1.0 / 3.0
    elif gid == "crash":
        target = float(params.get("target_multiplier") or 2.0)
        edge = float(g.get("house_edge") or 0.03)
        p = max(0.01, min(0.99, (1.0 - edge) / max(target, 1.01)))
    elif gid == "mines":
        tiles = int(g.get("tiles") or 25)
        mines = int(params.get("mines") or g.get("default_mines") or 3)
        safe = max(tiles - mines, 1)
        p = safe / max(tiles, 1)
    elif gid.startswith("slot"):
        p = 0.28
    elif gid == "plinko" or gid == "wheel":
        p = 0.45
    else:
        p = 0.4

    return {
        "game_id": gid,
        "win_probability": round(p, 4),
        "lose_probability": round(1.0 - p, 4),
    }


def rtp_estimate(game_id: str) -> Dict[str, Any]:
    g = _game_cfg(game_id)
    gid = (game_id or "").strip().lower()
    if g.get("rtp_estimate") is not None:
        rtp = float(g["rtp_estimate"])
    elif g.get("payout_multiplier"):
        mult = float(g["payout_multiplier"])
        wp = win_probability_estimate(gid).get("win_probability", 0.5)
        rtp = round(mult * wp * 100, 2)
    elif g.get("house_edge") is not None:
        rtp = round((1.0 - float(g["house_edge"])) * 100, 2)
    else:
        rtp = 96.0
    return {"game_id": gid, "rtp_percent": rtp, "house_edge_percent": round(100.0 - rtp, 2)}


def expected_value(bet: float, game_id: str, **params) -> Dict[str, Any]:
    bet = max(float(bet or 0), 0)
    gid = (game_id or "").strip().lower()
    g = _game_cfg(gid)
    wp = win_probability_estimate(gid, **params).get("win_probability", 0.5)
    mult = float(g.get("payout_multiplier") or params.get("payout_multiplier") or 1.9)
    if gid == "dice":
        mult = float(g.get("payout_multiplier") or 4.0)
    win_amt = bet * mult
    ev = win_amt * wp - bet * (1.0 - wp)
    return {
        "game_id": gid,
        "bet": bet,
        "win_probability": wp,
        "payout_multiplier": mult,
        "expected_net": round(ev, 4),
        "expected_roi_percent": round((ev / bet * 100) if bet > 0 else 0, 2),
    }


def kelly_bet_size(balance: float, win_prob: float, payout_multiplier: float, *, fraction: float = 1.0) -> Dict[str, Any]:
    balance = max(float(balance or 0), 0)
    p = max(0.0, min(float(win_prob or 0), 1.0))
    b = max(float(payout_multiplier or 1.0) - 1.0, 0.01)
    q = 1.0 - p
    kelly = (b * p - q) / b if b > 0 else 0.0
    kelly = max(0.0, kelly) * max(0.0, min(float(fraction or 1.0), 1.0))
    stake = round(balance * kelly, 4)
    return {
        "kelly_fraction": round(kelly, 4),
        "suggested_stake": stake,
        "balance": balance,
        "win_probability": p,
        "payout_multiplier": payout_multiplier,
    }


def calculate_for_game(game_id: str, *, bet: float = 10, balance: float = 1000, **params) -> Dict[str, Any]:
    gid = (game_id or "").strip().lower()
    guides = (_load_guides().get("games") or {}).get(gid) or {}
    rtp = rtp_estimate(gid)
    wp = win_probability_estimate(gid, **params)
    ev = expected_value(bet, gid, **params)
    g = _game_cfg(gid)
    mult = float(g.get("payout_multiplier") or ev.get("payout_multiplier") or 1.9)
    kelly = kelly_bet_size(balance, wp["win_probability"], mult)
    return {
        "success": True,
        "game_id": gid,
        "label": g.get("label") or gid,
        "guide": guides,
        "rtp": rtp,
        "win_probability": wp,
        "expected_value": ev,
        "kelly": kelly,
    }


def list_calculator_functions() -> List[Dict[str, str]]:
    return [
        {"id": "rtp_estimate", "description": "Return RTP % and house edge for a game."},
        {"id": "win_probability_estimate", "description": "Heuristic win chance for a game."},
        {"id": "expected_value", "description": "EV and ROI for a stake size."},
        {"id": "kelly_bet_size", "description": "Kelly criterion stake from balance and odds."},
        {"id": "calculate_for_game", "description": "All-in-one bundle for UI panels."},
    ]


def run_calculator(calc_id: str, **kwargs) -> Dict[str, Any]:
    cid = (calc_id or "").strip().lower()
    if cid == "rtp_estimate":
        return {"success": True, **rtp_estimate(kwargs.get("game_id", ""))}
    if cid == "win_probability_estimate":
        return {"success": True, **win_probability_estimate(kwargs.get("game_id", ""), **kwargs)}
    if cid == "expected_value":
        return {"success": True, **expected_value(float(kwargs.get("bet") or 10), kwargs.get("game_id", ""), **kwargs)}
    if cid == "kelly_bet_size":
        return {
            "success": True,
            **kelly_bet_size(
                float(kwargs.get("balance") or 0),
                float(kwargs.get("win_probability") or 0.5),
                float(kwargs.get("payout_multiplier") or 1.9),
                fraction=float(kwargs.get("fraction") or 1.0),
            ),
        }
    if cid == "calculate_for_game":
        return calculate_for_game(
            kwargs.get("game_id", ""),
            bet=float(kwargs.get("bet") or 10),
            balance=float(kwargs.get("balance") or 1000),
            **{k: v for k, v in kwargs.items() if k not in ("game_id", "bet", "balance")},
        )
    return {"success": False, "error": "unknown_calculator", "calculator_id": cid}
