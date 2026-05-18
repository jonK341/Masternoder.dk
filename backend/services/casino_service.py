"""
Virtual-coins casino: cosmetic betting only (no real money, no MN2 spend).
"""
from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_ROOT, "data", "casino_config.json")
_LOG_DIR = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _utcnow()).isoformat()


def _today_key() -> str:
    return _utcnow().strftime("%Y-%m-%d")


def _load_config() -> Dict[str, Any]:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _ledger_path() -> str:
    os.makedirs(_LOG_DIR, exist_ok=True)
    return os.path.join(_LOG_DIR, "casino_bets.jsonl")


def _append_ledger(row: Dict[str, Any]) -> None:
    path = _ledger_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        # Do not fail bets when log dir is not writable on the server.
        pass


def _read_ledger(user_id: str, limit: int = 25) -> List[Dict[str, Any]]:
    path = _ledger_path()
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("user_id") == user_id:
                    rows.append(row)
    except OSError:
        return []
    return list(reversed(rows[-limit:]))


def _count_bets_today(user_id: str) -> int:
    path = _ledger_path()
    if not os.path.isfile(path):
        return 0
    today = _today_key()
    count = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("user_id") == user_id and str(row.get("created_at") or "").startswith(today):
                    count += 1
    except OSError:
        return 0
    return count


def get_public_config() -> Dict[str, Any]:
    cfg = _load_config()
    games = cfg.get("games") if isinstance(cfg.get("games"), dict) else {}
    public_games = {}
    for key, game in games.items():
        if not isinstance(game, dict):
            continue
        row = {
            "label": game.get("label") or key,
            "payout_multiplier": float(game.get("payout_multiplier") or 0),
            "choices": game.get("choices") or [],
        }
        sides = game.get("sides")
        if sides is not None:
            row["sides"] = int(sides)
        public_games[key] = row
    return {
        "currency": cfg.get("currency") or "coins",
        "disclaimer": cfg.get("disclaimer") or "",
        "min_bet": int(cfg.get("min_bet") or 1),
        "max_bet": int(cfg.get("max_bet") or 500),
        "max_bets_per_day": int(cfg.get("max_bets_per_day") or 200),
        "games": public_games,
    }


def _user_coins(user_id: str) -> float:
    from backend.services.unified_points_database import unified_points_db

    result = unified_points_db.get_all_points(user_id)
    points = result.get("points") if isinstance(result, dict) else {}
    if not isinstance(points, dict):
        return 0.0
    return float(points.get("coins") or 0)


def get_balance(user_id: str) -> Dict[str, Any]:
    try:
        cfg = get_public_config()
        return {
            "success": True,
            "user_id": user_id,
            "currency": cfg["currency"],
            "balance": _user_coins(user_id),
            "bets_today": _count_bets_today(user_id),
            "max_bets_per_day": cfg["max_bets_per_day"],
            "min_bet": cfg["min_bet"],
            "max_bet": cfg["max_bet"],
            "disclaimer": cfg.get("disclaimer") or "",
            "games": cfg.get("games") or {},
        }
    except Exception as exc:
        return {
            "success": False,
            "user_id": user_id,
            "error": str(exc),
            "currency": "coins",
            "balance": 0,
            "bets_today": 0,
            "max_bets_per_day": 200,
            "min_bet": 5,
            "max_bet": 500,
            "disclaimer": "",
            "games": {},
        }


def _validate_bet(user_id: str, bet: float) -> Optional[str]:
    cfg = get_public_config()
    amount = int(bet)
    if amount < cfg["min_bet"]:
        return f"Minimum bet is {cfg['min_bet']} coins"
    if amount > cfg["max_bet"]:
        return f"Maximum bet is {cfg['max_bet']} coins"
    if _count_bets_today(user_id) >= cfg["max_bets_per_day"]:
        return "Daily bet limit reached"
    if _user_coins(user_id) < amount:
        return "Insufficient coins"
    return None


def _apply_coin_delta(user_id: str, delta: int, game: str, meta: Dict[str, Any]) -> None:
    from backend.services.unified_points_database import unified_points_db

    if delta == 0:
        return
    unified_points_db.add_points(
        user_id=user_id,
        point_type="coins",
        amount=float(delta),
        source="casino",
        metadata={"game": game, **meta},
    )


def _finalize_bet(
    user_id: str,
    game: str,
    bet: int,
    outcome: str,
    payout: int,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    net = payout - bet
    _apply_coin_delta(user_id, -bet, game, {"phase": "stake", **details})
    if payout > 0:
        _apply_coin_delta(user_id, payout, game, {"phase": "payout", **details})

    row = {
        "bet_id": str(uuid.uuid4()),
        "user_id": user_id,
        "game": game,
        "bet": bet,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "details": details,
        "created_at": _iso(),
    }
    _append_ledger(row)
    return {
        "success": True,
        "bet_id": row["bet_id"],
        "game": game,
        "bet": bet,
        "outcome": outcome,
        "payout": payout,
        "net": net,
        "balance": _user_coins(user_id),
        "details": details,
    }


def play_coin_flip(user_id: str, bet: float, choice: str) -> Dict[str, Any]:
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("coin_flip") or {}
    allowed = [c.lower() for c in (game_cfg.get("choices") or ["heads", "tails"])]
    pick = (choice or "").strip().lower()
    if pick not in allowed:
        return {"success": False, "error": f"choice must be one of {allowed}"}
    err = _validate_bet(user_id, bet)
    if err:
        return {"success": False, "error": err}
    amount = int(bet)
    result = random.choice(allowed)
    multiplier = float(game_cfg.get("payout_multiplier") or 1.9)
    payout = int(round(amount * multiplier)) if result == pick else 0
    outcome = "win" if payout > 0 else "loss"
    return _finalize_bet(
        user_id,
        "coin_flip",
        amount,
        outcome,
        payout,
        {"choice": pick, "result": result, "multiplier": multiplier},
    )


def play_dice(user_id: str, bet: float, guess: int) -> Dict[str, Any]:
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("dice") or {}
    sides = int(game_cfg.get("sides") or 6)
    try:
        pick = int(guess)
    except (TypeError, ValueError):
        return {"success": False, "error": "guess must be an integer"}
    if pick < 1 or pick > sides:
        return {"success": False, "error": f"guess must be between 1 and {sides}"}
    err = _validate_bet(user_id, bet)
    if err:
        return {"success": False, "error": err}
    amount = int(bet)
    roll = random.randint(1, sides)
    multiplier = float(game_cfg.get("payout_multiplier") or 4.0)
    payout = int(round(amount * multiplier)) if roll == pick else 0
    outcome = "win" if payout > 0 else "loss"
    return _finalize_bet(
        user_id,
        "dice",
        amount,
        outcome,
        payout,
        {"guess": pick, "roll": roll, "sides": sides, "multiplier": multiplier},
    )


def play_rps_bet(user_id: str, bet: float, choice: str) -> Dict[str, Any]:
    cfg = get_public_config()
    game_cfg = (cfg.get("games") or {}).get("rps_bet") or {}
    allowed = [c.lower() for c in (game_cfg.get("choices") or ["rock", "paper", "scissors"])]
    pick = (choice or "").strip().lower()
    if pick not in allowed:
        return {"success": False, "error": f"choice must be one of {allowed}"}
    err = _validate_bet(user_id, bet)
    if err:
        return {"success": False, "error": err}
    amount = int(bet)
    opponent = random.choice(allowed)
    beats = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    if pick == opponent:
        outcome = "draw"
        payout = amount
    elif beats.get(pick) == opponent:
        outcome = "win"
        multiplier = float(game_cfg.get("payout_multiplier") or 2.0)
        payout = int(round(amount * multiplier))
    else:
        outcome = "loss"
        payout = 0
    return _finalize_bet(
        user_id,
        "rps_bet",
        amount,
        outcome,
        payout,
        {"choice": pick, "opponent": opponent, "multiplier": float(game_cfg.get("payout_multiplier") or 2.0)},
    )


def get_history(user_id: str, limit: int = 25) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit or 25), 100))
    return {"success": True, "user_id": user_id, "history": _read_ledger(user_id, safe_limit)}
