"""Casino competition — rival boards, achievement races, crew leaderboards, streak battles."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOCK = threading.Lock()
_SOCIAL_PATH = os.path.join(_ROOT, "data", "social_structure.json")


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _races_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_achievement_races.json")


def _rival_stats_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_rival_stats.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _week_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_races() -> Dict[str, Any]:
    path = _races_path()
    if not os.path.isfile(path):
        return {"races": {}, "winners": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"races": {}, "winners": {}}
    except Exception:
        return {"races": {}, "winners": {}}


def _save_races(data: Dict[str, Any]) -> None:
    try:
        with open(_races_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _load_rival_stats() -> Dict[str, Any]:
    path = _rival_stats_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_rival_stats(data: Dict[str, Any]) -> None:
    try:
        with open(_rival_stats_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _load_social() -> Dict[str, Any]:
    if not os.path.isfile(_SOCIAL_PATH):
        return {"friends": {}, "crews": [], "user_crews": {}}
    try:
        with open(_SOCIAL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"friends": {}, "crews": [], "user_crews": {}}
    except Exception:
        return {"friends": {}, "crews": [], "user_crews": {}}


def _peer_ids(user_id: str) -> List[str]:
    try:
        from backend.services.casino_service import _social_peer_ids
        return _social_peer_ids(user_id)
    except Exception:
        social = _load_social()
        return list((social.get("friends") or {}).get(user_id, []) or [])


def _ledger_net_since(user_id: str, since: datetime, currency: str = "coins") -> float:
    try:
        from backend.services.casino_service import _ledger_path, _normalize_currency
        path = _ledger_path()
        currency = _normalize_currency(currency)
        total = 0.0
        if not os.path.isfile(path):
            return 0.0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("user_id") != user_id:
                    continue
                if _normalize_currency(row.get("currency") or "coins") != currency:
                    continue
                ts = str(row.get("created_at") or "")
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if dt >= since:
                    total += float(row.get("net") or 0)
        return total
    except Exception:
        return 0.0


def get_rival_board(user_id: str, period: str = "week", currency: str = "coins") -> Dict[str, Any]:
    """Net wins vs peers — who is 'Rival of the week'."""
    period = (period or "week").lower()
    now = datetime.now(timezone.utc)
    if period == "month":
        since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_key = _month_key()
    else:
        since = now - timedelta(days=now.weekday())
        since = since.replace(hour=0, minute=0, second=0, microsecond=0)
        period_key = _week_key()

    peers = _peer_ids(user_id)
    my_net = _ledger_net_since(user_id, since, currency)
    rows = [{"user_id": user_id, "net": round(my_net, 2), "is_you": True}]
    for pid in peers:
        net = _ledger_net_since(pid, since, currency)
        rows.append({"user_id": pid, "net": round(net, 2), "is_you": False})
    rows.sort(key=lambda r: r.get("net") or 0, reverse=True)

    rival_of_week = None
    if len(rows) > 1:
        top = rows[0]
        if top.get("user_id") != user_id and (top.get("net") or 0) > my_net:
            rival_of_week = top.get("user_id")
        elif my_net > 0 and rows[0].get("user_id") == user_id:
            rival_of_week = user_id

    beats = 0
    for r in rows:
        if r.get("user_id") != user_id and (r.get("net") or 0) < my_net:
            beats += 1

    with _LOCK:
        stats = _load_rival_stats()
        user_stats = stats.setdefault(user_id, {"beats": {}, "period": period_key})
        if user_stats.get("period") != period_key:
            user_stats = {"beats": {}, "period": period_key}
            stats[user_id] = user_stats
        for r in rows:
            pid = r.get("user_id")
            if pid and pid != user_id and (r.get("net") or 0) < my_net:
                user_stats["beats"][pid] = int(user_stats["beats"].get(pid) or 0) + 1
        _save_rival_stats(stats)
        total_beats = sum(user_stats.get("beats", {}).values())

    return {
        "success": True,
        "user_id": user_id,
        "period": period,
        "period_key": period_key,
        "currency": currency,
        "your_net": round(my_net, 2),
        "rival_of_week": rival_of_week,
        "rival_beats": total_beats,
        "leaderboard": rows[:15],
        "streak_battle": _duel_streak_info(user_id),
    }


def _duel_streak_info(user_id: str) -> Dict[str, Any]:
    try:
        from backend.services import casino_progression
        state = casino_progression._load_state().get(user_id) or {}
        return {
            "duel_streak": int(state.get("duel_streak") or 0),
            "best_duel_streak": int(state.get("best_duel_streak") or 0),
        }
    except Exception:
        return {"duel_streak": 0, "best_duel_streak": 0}


def get_achievement_races(user_id: str) -> Dict[str, Any]:
    """First-to-unlock competitive achievements."""
    races_def = [
        {"id": "first_jackpot", "label": "First Jackpot Hit", "icon": "💰", "prize_coins": 1000, "metric": "jackpot_hits", "target": 1},
        {"id": "first_duel_10", "label": "First to 10 Duel Wins", "icon": "⚔️", "prize_coins": 500, "metric": "duel_wins", "target": 10},
        {"id": "first_shop_15", "label": "First to Own 15 Shop Items", "icon": "🛍️", "prize_coins": 300, "metric": "shop_items", "target": 15},
    ]
    with _LOCK:
        data = _load_races()
        winners = data.get("winners") if isinstance(data.get("winners"), dict) else {}

    rows = []
    for race in races_def:
        rid = race["id"]
        winner = winners.get(rid)
        rows.append({
            **race,
            "winner_id": winner.get("user_id") if isinstance(winner, dict) else None,
            "won_at": winner.get("won_at") if isinstance(winner, dict) else None,
            "you_won": isinstance(winner, dict) and winner.get("user_id") == user_id,
            "open": winner is None,
        })
    return {"success": True, "user_id": user_id, "races": rows}


def try_claim_race(user_id: str, race_id: str, metric_value: float, target: float) -> Optional[Dict[str, Any]]:
    """Award first-to-finish race if still open."""
    if metric_value < target:
        return None
    with _LOCK:
        data = _load_races()
        winners = data.setdefault("winners", {})
        if race_id in winners:
            return None
        winners[race_id] = {"user_id": user_id, "won_at": _iso()}
        _save_races(data)

    prize_map = {"first_jackpot": 1000, "first_duel_10": 500, "first_shop_15": 300}
    prize = prize_map.get(race_id, 250)
    try:
        from backend.services.casino_service import _apply_coin_delta
        _apply_coin_delta(user_id, prize, "achievement_race", {"race_id": race_id})
    except Exception:
        pass
    try:
        from backend.services import casino_progression
        casino_progression.on_event(user_id, "race_won", {"race_id": race_id, "prize": prize})
    except Exception:
        pass
    return {"race_id": race_id, "prize_coins": prize}


def get_crew_casino_leaderboard(user_id: str, currency: str = "coins") -> Dict[str, Any]:
    """Aggregate casino net per crew from social_structure."""
    social = _load_social()
    crews = social.get("crews") or []
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)

    rows = []
    my_crew_id = (social.get("user_crews") or {}).get(user_id)
    for crew in crews:
        if not isinstance(crew, dict):
            continue
        cid = crew.get("id")
        members = crew.get("member_ids") or crew.get("members") or []
        if not members:
            continue
        total_net = sum(_ledger_net_since(str(m), since, currency) for m in members)
        rows.append({
            "crew_id": cid,
            "name": crew.get("name") or cid,
            "member_count": len(members),
            "week_net": round(total_net, 2),
            "is_yours": cid == my_crew_id,
        })
    rows.sort(key=lambda r: r.get("week_net") or 0, reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return {
        "success": True,
        "user_id": user_id,
        "currency": currency,
        "crew_leaderboard": rows[:20],
        "your_crew_id": my_crew_id,
    }


def on_duel_settled(winner_id: Optional[str], loser_id: Optional[str], challenger_id: str, acceptor_id: str) -> None:
    """Update rival beat counts and duel streaks after a duel resolves."""
    try:
        from backend.services import casino_progression
        if winner_id:
            casino_progression.on_event(winner_id, "duel_win", {"opponent": acceptor_id if winner_id == challenger_id else challenger_id})
            loser = acceptor_id if winner_id == challenger_id else challenger_id
            casino_progression.on_event(loser, "duel_loss", {})
    except Exception:
        pass


def on_tournament_close(user_id: str, place: int) -> None:
    try:
        from backend.services import casino_progression
        casino_progression.on_event(user_id, "tournament_finish", {"place": place})
    except Exception:
        pass
