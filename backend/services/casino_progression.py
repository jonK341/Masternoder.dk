"""
Casino progression — XP, levels, VIP tiers, achievements, daily lucky wheel.

Rewards are paid in coins unless explicitly configured otherwise. Hooked into
the bet ledger via casino_service._append_ledger (on_bet). No RTP perks — VIP
only affects caps, badges, and daily-wheel slices.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOCK = threading.Lock()
_ACHIEVEMENT_CATALOG_PATH = os.path.join(_ROOT, "data", "casino_achievements.json")


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _state_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_progression.json")


def _achievements_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_achievements.json")


def _load_config() -> Dict[str, Any]:
    try:
        from backend.services.casino_service import _load_config as load_casino_config
        cfg = load_casino_config()
    except Exception:
        cfg = {}
    prog = cfg.get("progression") if isinstance(cfg.get("progression"), dict) else {}
    return prog


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(data: Dict[str, Any]) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _load_achievements() -> Dict[str, Any]:
    path = _achievements_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_achievements(data: Dict[str, Any]) -> None:
    try:
        with open(_achievements_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _coins_equivalent(bet: float, currency: str, cfg: Dict[str, Any]) -> float:
    currency = (currency or "coins").lower()
    if currency == "coins":
        return float(bet or 0)
    if currency == "mn2":
        rate = float(cfg.get("mn2_xp_per_unit") or 100)
        return float(bet or 0) * rate
    if currency in ("usd", "fiat"):
        rate = float(cfg.get("usd_xp_per_unit") or 50)
        return float(bet or 0) * rate
    return float(bet or 0)


def _level_for_xp(xp: float, levels: List[Dict[str, Any]]) -> Dict[str, Any]:
    current = levels[0] if levels else {"level": 1, "xp_required": 0, "reward_coins": 0}
    for row in levels:
        if xp >= float(row.get("xp_required") or 0):
            current = row
        else:
            break
    nxt = None
    for row in levels:
        if float(row.get("xp_required") or 0) > xp:
            nxt = row
            break
    return {
        "level": int(current.get("level") or 1),
        "title": current.get("title") or f"Level {current.get('level', 1)}",
        "xp": round(xp, 2),
        "next_level_xp": float(nxt.get("xp_required")) if nxt else None,
        "reward_coins": int(current.get("reward_coins") or 0),
    }


def _vip_tier(lifetime_wager: float, tiers: List[Dict[str, Any]]) -> Dict[str, Any]:
    current = tiers[0] if tiers else {"id": "bronze", "label": "Bronze", "min_wager": 0}
    for row in tiers:
        if lifetime_wager >= float(row.get("min_wager") or 0):
            current = row
    return {
        "id": current.get("id") or "bronze",
        "label": current.get("label") or "Bronze",
        "badge": current.get("badge") or "🥉",
        "min_wager": float(current.get("min_wager") or 0),
    }


def _default_levels() -> List[Dict[str, Any]]:
    return [
        {"level": 1, "title": "Rookie", "xp_required": 0, "reward_coins": 0},
        {"level": 2, "title": "Regular", "xp_required": 500, "reward_coins": 50},
        {"level": 3, "title": "High Roller", "xp_required": 2000, "reward_coins": 150},
        {"level": 4, "title": "VIP Guest", "xp_required": 5000, "reward_coins": 300},
        {"level": 5, "title": "House Legend", "xp_required": 15000, "reward_coins": 750},
    ]


def _default_vip_tiers() -> List[Dict[str, Any]]:
    return [
        {"id": "bronze", "label": "Bronze", "badge": "🥉", "min_wager": 0},
        {"id": "silver", "label": "Silver", "badge": "🥈", "min_wager": 5000},
        {"id": "gold", "label": "Gold", "badge": "🥇", "min_wager": 25000},
        {"id": "platinum", "label": "Platinum", "badge": "💎", "min_wager": 100000},
        {"id": "diamond", "label": "Diamond", "badge": "👑", "min_wager": 500000},
    ]


def _default_achievements() -> List[Dict[str, Any]]:
    return [
        {"id": "first_bet", "label": "First Wager", "icon": "🎲", "coins": 25, "metric": "bets", "target": 1},
        {"id": "first_win", "label": "First Win", "icon": "🏆", "coins": 50, "metric": "wins", "target": 1},
        {"id": "ten_wins", "label": "Ten Wins", "icon": "🔥", "coins": 100, "metric": "wins", "target": 10},
        {"id": "tried_crash", "label": "Crash Pilot", "icon": "🚀", "coins": 30, "metric": "game_bets", "game": "crash", "target": 1},
        {"id": "tried_slots", "label": "Slot Spinner", "icon": "🎰", "coins": 30, "metric": "game_prefix_bets", "game_prefix": "slot_", "target": 1},
        {"id": "first_jackpot", "label": "Jackpot Hunter", "icon": "💰", "coins": 500, "metric": "jackpot_hits", "target": 1},
    ]


def _load_achievement_catalog() -> List[Dict[str, Any]]:
    if os.path.isfile(_ACHIEVEMENT_CATALOG_PATH):
        try:
            with open(_ACHIEVEMENT_CATALOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = data.get("achievements") if isinstance(data, dict) else []
            if rows:
                return [r for r in rows if isinstance(r, dict)]
        except Exception:
            pass
    cfg = _load_config()
    return cfg.get("achievements") or _default_achievements()


def _default_user_state() -> Dict[str, Any]:
    return {
        "xp": 0.0,
        "lifetime_wager_coins": 0.0,
        "lifetime_net": 0.0,
        "wins": 0,
        "bets": 0,
        "win_streak": 0,
        "best_win_streak": 0,
        "games_tried": [],
        "game_bets": {},
        "jackpot_hits": 0,
        "crash_cashouts": 0,
        "mines_cashouts": 0,
        "duel_wins": 0,
        "duel_wins_today": 0,
        "duel_streak": 0,
        "best_duel_streak": 0,
        "duel_wins_date": None,
        "tournament_wins": 0,
        "tournament_top10": 0,
        "best_tournament_place": 999,
        "rival_beats": 0,
        "daily_wheel_date": None,
        "daily_bets_streak": 0,
        "last_bet_date": None,
    }


def _metric_value(user: Dict[str, Any], user_id: str, ach: Dict[str, Any]) -> float:
    metric = ach.get("metric") or ""
    if metric == "bets":
        return float(user.get("bets") or 0)
    if metric == "wins":
        return float(user.get("wins") or 0)
    if metric == "win_streak":
        return float(user.get("best_win_streak") or user.get("win_streak") or 0)
    if metric == "jackpot_hits":
        return float(user.get("jackpot_hits") or 0)
    if metric == "crash_cashouts":
        return float(user.get("crash_cashouts") or 0)
    if metric == "game_bets":
        gb = user.get("game_bets") or {}
        return float(gb.get(ach.get("game") or "") or 0)
    if metric == "game_prefix_bets":
        prefix = ach.get("game_prefix") or ""
        gb = user.get("game_bets") or {}
        return float(sum(v for k, v in gb.items() if str(k).startswith(prefix)))
    if metric == "duel_wins":
        return float(user.get("duel_wins") or 0)
    if metric == "duel_wins_today":
        return float(user.get("duel_wins_today") or 0) if user.get("duel_wins_date") == _today_key() else 0.0
    if metric == "tournament_wins":
        return float(user.get("tournament_wins") or 0)
    if metric == "tournament_top10":
        return float(user.get("tournament_top10") or 0)
    if metric == "shop_items_owned":
        try:
            from backend.services import casino_shop_service
            return float(casino_shop_service.owned_count(user_id))
        except Exception:
            return 0.0
    if metric == "trophies_owned":
        try:
            from backend.services import casino_trophies_service
            return float(casino_trophies_service.trophy_count(user_id))
        except Exception:
            return 0.0
    if metric == "rival_beats":
        return float(user.get("rival_beats") or 0)
    if metric == "lifetime_net_positive":
        return max(0.0, float(user.get("lifetime_net") or 0))
    if metric == "race_first":
        race_id = ach.get("race_id") or ""
        try:
            from backend.services import casino_competition_service
            races = casino_competition_service.get_achievement_races(user_id).get("races") or []
            for r in races:
                if r.get("id") == race_id and r.get("you_won"):
                    return 1.0
        except Exception:
            pass
        return 0.0
    # Legacy field support
    if ach.get("wins_required"):
        return float(user.get("wins") or 0)
    if ach.get("game"):
        gb = user.get("game_bets") or {}
        return float(gb.get(ach.get("game") or "") or 0)
    if ach.get("game_prefix"):
        prefix = ach.get("game_prefix") or ""
        gb = user.get("game_bets") or {}
        return float(sum(v for k, v in gb.items() if str(k).startswith(prefix)))
    if ach.get("jackpot"):
        return float(user.get("jackpot_hits") or 0)
    return 0.0


def _achievement_target(ach: Dict[str, Any]) -> float:
    if ach.get("target") is not None:
        return float(ach["target"])
    if ach.get("wins_required"):
        return float(ach["wins_required"])
    return 1.0


def _check_achievements(user_id: str, user: Dict[str, Any]) -> List[Dict[str, Any]]:
    catalog = _load_achievement_catalog()
    ach_data = _load_achievements()
    unlocked = set(ach_data.get(user_id) or [])
    events: List[Dict[str, Any]] = []
    for ach in catalog:
        aid = ach.get("id")
        if not aid or aid in unlocked:
            continue
        progress = _metric_value(user, user_id, ach)
        target = _achievement_target(ach)
        if progress >= target:
            unlocked.add(aid)
            events.append({"type": "achievement", "id": aid, "coins": int(ach.get("coins") or 0)})
    if unlocked != set(ach_data.get(user_id) or []):
        ach_data[user_id] = sorted(unlocked)
        _save_achievements(ach_data)
    return events


def _apply_achievement_rewards(user_id: str, events: List[Dict[str, Any]]) -> None:
    for ev in events:
        if ev.get("type") == "achievement" and ev.get("coins", 0) > 0:
            try:
                from backend.services.casino_service import _apply_coin_delta
                _apply_coin_delta(user_id, int(ev["coins"]), "progression", {"achievement": ev.get("id")})
            except Exception:
                pass


def _post_progress_hooks(user_id: str, user: Dict[str, Any]) -> None:
    try:
        from backend.services import casino_trophies_service
        casino_trophies_service.check_and_award(user_id, user)
    except Exception:
        pass
    try:
        from backend.services import casino_competition_service
        if int(user.get("jackpot_hits") or 0) >= 1:
            casino_competition_service.try_claim_race(user_id, "first_jackpot", float(user["jackpot_hits"]), 1)
        if int(user.get("duel_wins") or 0) >= 10:
            casino_competition_service.try_claim_race(user_id, "first_duel_10", float(user["duel_wins"]), 10)
        from backend.services import casino_shop_service
        owned = casino_shop_service.owned_count(user_id)
        if owned >= 15:
            casino_competition_service.try_claim_race(user_id, "first_shop_15", float(owned), 15)
    except Exception:
        pass


def get_profile(user_id: str) -> Dict[str, Any]:
    cfg = _load_config()
    levels = cfg.get("levels") or _default_levels()
    tiers = cfg.get("vip_tiers") or _default_vip_tiers()
    with _LOCK:
        state = _load_state()
        user = state.get(user_id) if isinstance(state.get(user_id), dict) else {}
        xp = float(user.get("xp") or 0)
        lifetime = float(user.get("lifetime_wager_coins") or 0)
        ach = _load_achievements().get(user_id) or []
    level = _level_for_xp(xp, levels)
    vip = _vip_tier(lifetime, tiers)
    return {
        "success": True,
        "user_id": user_id,
        "xp": level,
        "vip": vip,
        "lifetime_wager_coins": int(lifetime),
        "achievements_unlocked": list(ach) if isinstance(ach, list) else [],
        "daily_wheel_spun_today": user.get("daily_wheel_date") == _today_key(),
    }


def list_achievements(user_id: str) -> Dict[str, Any]:
    catalog = _load_achievement_catalog()
    unlocked = set(_load_achievements().get(user_id) or [])
    user = (_load_state().get(user_id) or {}) if user_id else {}
    rows = []
    for a in catalog:
        progress = _metric_value(user, user_id, a)
        target = _achievement_target(a)
        rows.append({
            **a,
            "unlocked": a.get("id") in unlocked,
            "progress": round(progress, 2),
            "target": target,
            "progress_pct": min(100, int(100 * progress / target)) if target > 0 else 0,
        })
    return {"success": True, "user_id": user_id, "achievements": rows}


def on_bet(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Award XP and check achievements after a settled bet. Best-effort."""
    if not isinstance(row, dict) or not row.get("user_id"):
        return None
    if row.get("exclude_leaderboard"):
        return None
    user_id = str(row["user_id"])
    cfg = _load_config()
    xp_rate = float(cfg.get("xp_per_coin_wagered") or 1.0)
    coins_eq = _coins_equivalent(float(row.get("bet") or 0), str(row.get("currency") or "coins"), cfg)
    xp_gain = round(coins_eq * xp_rate, 2)
    game = str(row.get("game") or "")
    outcome = str(row.get("outcome") or "")
    net = float(row.get("net") or 0)
    details = row.get("details") if isinstance(row.get("details"), dict) else {}
    events: List[Dict[str, Any]] = []
    today = _today_key()

    with _LOCK:
        state = _load_state()
        user = state.setdefault(user_id, _default_user_state())
        prev_level = _level_for_xp(float(user.get("xp") or 0), cfg.get("levels") or _default_levels())
        user["xp"] = round(float(user.get("xp") or 0) + xp_gain, 2)
        user["lifetime_wager_coins"] = round(float(user.get("lifetime_wager_coins") or 0) + coins_eq, 2)
        user["lifetime_net"] = round(float(user.get("lifetime_net") or 0) + net, 2)
        user["bets"] = int(user.get("bets") or 0) + 1
        if outcome == "win" and net > 0:
            user["wins"] = int(user.get("wins") or 0) + 1
            user["win_streak"] = int(user.get("win_streak") or 0) + 1
            user["best_win_streak"] = max(int(user.get("best_win_streak") or 0), user["win_streak"])
        else:
            user["win_streak"] = 0
        tried = set(user.get("games_tried") or [])
        tried.add(game)
        user["games_tried"] = sorted(tried)
        gb = dict(user.get("game_bets") or {})
        gb[game] = int(gb.get(game) or 0) + 1
        user["game_bets"] = gb
        if bool(row.get("jackpot")):
            user["jackpot_hits"] = int(user.get("jackpot_hits") or 0) + 1
        if game == "crash" and details.get("phase") == "cashout" and outcome == "win":
            user["crash_cashouts"] = int(user.get("crash_cashouts") or 0) + 1
        if game == "mines" and details.get("phase") == "cashout" and outcome == "win":
            user["mines_cashouts"] = int(user.get("mines_cashouts") or 0) + 1
        if user.get("last_bet_date") == today:
            pass
        elif user.get("last_bet_date"):
            from datetime import timedelta
            try:
                last = datetime.strptime(str(user["last_bet_date"]), "%Y-%m-%d").date()
                cur = datetime.strptime(today, "%Y-%m-%d").date()
                if (cur - last).days == 1:
                    user["daily_bets_streak"] = int(user.get("daily_bets_streak") or 0) + 1
                else:
                    user["daily_bets_streak"] = 1
            except ValueError:
                user["daily_bets_streak"] = 1
        else:
            user["daily_bets_streak"] = 1
        user["last_bet_date"] = today
        new_level = _level_for_xp(float(user["xp"]), cfg.get("levels") or _default_levels())
        events.extend(_check_achievements(user_id, user))
        _save_state(state)

    if new_level["level"] > prev_level["level"]:
        reward = int(new_level.get("reward_coins") or 0)
        if reward > 0:
            try:
                from backend.services.casino_service import _apply_coin_delta
                _apply_coin_delta(user_id, reward, "progression", {"reason": "level_up", "level": new_level["level"]})
                events.append({"type": "level_up", "level": new_level["level"], "coins": reward})
            except Exception:
                pass

    _apply_achievement_rewards(user_id, events)
    _post_progress_hooks(user_id, user)

    if not events and xp_gain <= 0:
        return None
    return {"xp_gain": xp_gain, "events": events}


def on_event(user_id: str, event_type: str, payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Handle duel, tournament, shop, and race events."""
    payload = payload or {}
    events: List[Dict[str, Any]] = []
    today = _today_key()
    with _LOCK:
        state = _load_state()
        user = state.setdefault(user_id, _default_user_state())
        if event_type == "duel_win":
            user["duel_wins"] = int(user.get("duel_wins") or 0) + 1
            user["duel_streak"] = int(user.get("duel_streak") or 0) + 1
            user["best_duel_streak"] = max(int(user.get("best_duel_streak") or 0), user["duel_streak"])
            if user.get("duel_wins_date") != today:
                user["duel_wins_today"] = 1
                user["duel_wins_date"] = today
            else:
                user["duel_wins_today"] = int(user.get("duel_wins_today") or 0) + 1
        elif event_type == "duel_loss":
            user["duel_streak"] = 0
        elif event_type == "tournament_finish":
            place = int(payload.get("place") or 999)
            user["best_tournament_place"] = min(int(user.get("best_tournament_place") or 999), place)
            if place == 1:
                user["tournament_wins"] = int(user.get("tournament_wins") or 0) + 1
            if place <= 10:
                user["tournament_top10"] = int(user.get("tournament_top10") or 0) + 1
        elif event_type == "shop_purchase":
            pass
        elif event_type == "trophy_unlock":
            pass
        elif event_type == "race_won":
            pass
        events.extend(_check_achievements(user_id, user))
        _save_state(state)
    _apply_achievement_rewards(user_id, events)
    _post_progress_hooks(user_id, user)
    return {"events": events} if events else None


def spin_daily_wheel(user_id: str) -> Dict[str, Any]:
    """One free lucky-wheel spin per day — coin prizes only."""
    from backend.services import casino_rng
    from backend.services.engines import wheel as wheel_engine

    cfg = _load_config()
    slices = cfg.get("daily_wheel_slices") or [
        {"multiplier": 0, "weight": 30, "label": "10 coins", "coins": 10},
        {"multiplier": 0, "weight": 25, "label": "25 coins", "coins": 25},
        {"multiplier": 0, "weight": 20, "label": "50 coins", "coins": 50},
        {"multiplier": 0, "weight": 15, "label": "100 coins", "coins": 100},
        {"multiplier": 0, "weight": 8, "label": "250 coins", "coins": 250},
        {"multiplier": 0, "weight": 2, "label": "1000 coins", "coins": 1000},
    ]
    today = _today_key()
    with _LOCK:
        state = _load_state()
        user = state.setdefault(user_id, {})
        if user.get("daily_wheel_date") == today:
            return {"success": False, "error": "Daily wheel already spun today", "code": "DAILY_WHEEL_USED"}
        user["daily_wheel_date"] = today
        _save_state(state)

    proof = casino_rng.draw(user_id)
    segments = [{"multiplier": float(s.get("coins") or 0), "weight": float(s.get("weight") or 1)} for s in slices]
    spin_result = wheel_engine.spin(proof["float"], segments)
    idx = int(spin_result["index"])
    prize = int(slices[idx].get("coins") or 0)
    label = slices[idx].get("label") or f"{prize} coins"
    if prize > 0:
        try:
            from backend.services.casino_service import _apply_coin_delta
            _apply_coin_delta(user_id, prize, "daily_wheel", {"slice": idx, "label": label})
        except Exception:
            pass
    return {
        "success": True,
        "slice_index": idx,
        "label": label,
        "coins_awarded": prize,
        "fairness": {
            "server_seed_hash": proof["server_seed_hash"],
            "client_seed": proof["client_seed"],
            "nonce": proof["nonce"],
        },
    }
