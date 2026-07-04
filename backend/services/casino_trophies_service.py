"""Casino trophies — config-driven unlocks with coin rewards."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional, Set

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOCK = threading.Lock()
_TROPHIES_PATH = os.path.join(_ROOT, "data", "casino_trophies.json")


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _unlocked_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_trophies_unlocked.json")


def _load_catalog() -> List[Dict[str, Any]]:
    if not os.path.isfile(_TROPHIES_PATH):
        return []
    try:
        with open(_TROPHIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("trophies") if isinstance(data, dict) else []
        return [r for r in rows if isinstance(r, dict)]
    except Exception:
        return []


def _load_unlocked() -> Dict[str, List[str]]:
    path = _unlocked_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_unlocked(data: Dict[str, List[str]]) -> None:
    try:
        with open(_unlocked_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def unlocked_set(user_id: str) -> Set[str]:
    return set(_load_unlocked().get(user_id) or [])


def trophy_count(user_id: str) -> int:
    return len(unlocked_set(user_id))


def list_trophies(user_id: str) -> Dict[str, Any]:
    unlocked = unlocked_set(user_id)
    rows = []
    for t in _load_catalog():
        tid = t.get("id")
        rows.append({
            **t,
            "unlocked": tid in unlocked,
        })
    return {"success": True, "user_id": user_id, "trophies": rows, "unlocked_count": len(unlocked)}


def _award_coins(user_id: str, coins: int, trophy_id: str) -> None:
    if coins <= 0:
        return
    try:
        from backend.services.casino_service import _apply_coin_delta
        _apply_coin_delta(user_id, coins, "casino_trophy", {"trophy_id": trophy_id})
    except Exception:
        pass


def _sync_global_trophy(user_id: str, trophy_id: str, coins: int) -> None:
    try:
        from backend.services.trophies_db_service import award_trophy
        award_trophy(user_id, f"casino_{trophy_id}", reward=float(coins or 100))
    except Exception:
        pass


def unlock_trophy(user_id: str, trophy_id: str) -> Optional[Dict[str, Any]]:
    catalog = {t.get("id"): t for t in _load_catalog()}
    trophy = catalog.get(trophy_id)
    if not trophy:
        return None
    with _LOCK:
        data = _load_unlocked()
        user_list = list(data.get(user_id) or [])
        if trophy_id in user_list:
            return None
        user_list.append(trophy_id)
        data[user_id] = user_list
        _save_unlocked(data)
    coins = int(trophy.get("coins") or 0)
    _award_coins(user_id, coins, trophy_id)
    _sync_global_trophy(user_id, trophy_id, coins)
    try:
        from backend.services import casino_progression
        casino_progression.on_event(user_id, "trophy_unlock", {"trophy_id": trophy_id, "count": len(user_list)})
    except Exception:
        pass
    return {"trophy_id": trophy_id, "name": trophy.get("name"), "coins": coins}


def _metric_value(user_id: str, stats: Dict[str, Any], criteria: Dict[str, Any]) -> float:
    ctype = criteria.get("type") or ""
    if ctype == "win_streak":
        return float(stats.get("win_streak") or 0)
    if ctype == "jackpot_hit":
        return float(stats.get("jackpot_hits") or 0)
    if ctype == "duel_wins":
        return float(stats.get("duel_wins") or 0)
    if ctype == "duel_streak":
        return float(stats.get("duel_streak") or 0)
    if ctype == "games_tried":
        return float(len(stats.get("games_tried") or []))
    if ctype == "lifetime_wager":
        return float(stats.get("lifetime_wager_coins") or 0)
    if ctype == "daily_bets_streak":
        return float(stats.get("daily_bets_streak") or 0)
    if ctype == "crash_cashouts":
        return float(stats.get("crash_cashouts") or 0)
    if ctype == "game_bets":
        game = criteria.get("game") or ""
        gb = stats.get("game_bets") or {}
        return float(gb.get(game) or 0)
    if ctype == "mines_cashouts":
        return float(stats.get("mines_cashouts") or 0)
    if ctype == "shared_win":
        return float(stats.get("shared_wins") or 0)
    if ctype == "referral_casino_play":
        return float(stats.get("referral_casino_plays") or 0)
    if ctype == "shop_items_owned":
        try:
            from backend.services import casino_shop_service
            return float(casino_shop_service.owned_count(user_id))
        except Exception:
            return 0.0
    if ctype == "achievements_unlocked":
        try:
            from backend.services import casino_progression
            ach = casino_progression._load_achievements().get(user_id) or []
            return float(len(ach))
        except Exception:
            return 0.0
    if ctype == "rival_of_week":
        return float(stats.get("rival_of_week") or 0)
    if ctype == "tournament_place":
        return float(stats.get("best_tournament_place") or 999)
    return 0.0


def _criteria_met(user_id: str, stats: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
    ctype = criteria.get("type") or ""
    val = _metric_value(user_id, stats, criteria)
    if ctype == "tournament_place":
        place = int(criteria.get("place") or 0)
        place_max = int(criteria.get("place_max") or 0)
        best = int(stats.get("best_tournament_place") or 999)
        if place and best == place:
            return True
        if place_max and best <= place_max:
            return True
        return False
    target = float(criteria.get("count") or 1)
    return val >= target


def check_and_award(user_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Evaluate all trophy criteria against stats; award any newly unlocked."""
    unlocked = unlocked_set(user_id)
    awarded: List[Dict[str, Any]] = []
    for trophy in _load_catalog():
        tid = trophy.get("id")
        if not tid or tid in unlocked:
            continue
        criteria = trophy.get("criteria") if isinstance(trophy.get("criteria"), dict) else {}
        if _criteria_met(user_id, stats, criteria):
            result = unlock_trophy(user_id, tid)
            if result:
                awarded.append(result)
                unlocked.add(tid)
    return awarded
