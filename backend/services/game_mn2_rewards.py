"""Unified MN2 reward path for game, battle, quests, and starmap (Phase 11)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.activity_events_service import emit

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATE = os.path.join(_BASE, "data", "game_earn_state.json")

# Top-10 earn function ids (plan Phase 11).
TOP10_EARN = (
    "daily_multi_game_streak",
    "cross_game_combo",
    "first_win_of_day",
    "quest_trophy_chain",
    "leaderboard_rank_payout",
    "referral_social",
    "watch_to_earn",
    "compendium_completion",
    "casino_playthrough_rebate",
    "monitor_check_in",
)

_DEFAULT_AMOUNTS = {
    "daily_multi_game_streak": 0.01,
    "cross_game_combo": 0.015,
    "first_win_of_day": 0.02,
    "quest_trophy_chain": 0.025,
    "leaderboard_rank_payout": 0.05,
    "referral_social": 0.03,
    "watch_to_earn": 0.005,
    "compendium_completion": 0.1,
    "casino_playthrough_rebate": 0.01,
    "monitor_check_in": 0.002,
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> Dict[str, Any]:
    if not os.path.isfile(_STATE):
        return {"users": {}}
    try:
        with open(_STATE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"users": {}}
    except Exception:
        return {"users": {}}


def _save_state(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STATE), exist_ok=True)
    tmp = _STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _STATE)


def credit_mn2(
    user_id: str,
    amount: float,
    *,
    source: str,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}
    user_id = uid_or_err
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}

    meta = dict(metadata or {})
    meta["reference"] = reference
    meta["source"] = source

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    result = unified_points_db.add_points(
        user_id, "mn2_balance", amt, source=source, metadata=meta,
    )
    if not result.get("success"):
        return result
    if result.get("duplicate"):
        return result

    append_entry(
        user_id=user_id,
        entry_type=source,
        amount=amt,
        txid=reference,
        metadata=meta,
    )
    emit(
        "game_mn2_reward",
        user_id=user_id,
        channel="game",
        text=f"+{amt} MN2 ({source})",
        payload={"amount": amt, "source": source, "reference": reference},
    )
    return {"success": True, "amount": amt, "user_id": user_id, "source": source}


def list_top10_earn() -> Dict[str, Any]:
    return {
        "success": True,
        "earn_functions": [
            {"id": eid, "default_mn2": _DEFAULT_AMOUNTS.get(eid, 0.01)}
            for eid in TOP10_EARN
        ],
    }


def claim_earn(
    user_id: str,
    earn_id: str,
    *,
    amount: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Idempotent daily claim for one of the top-10 earn functions."""
    eid = (earn_id or "").strip().lower()
    if eid not in TOP10_EARN:
        return {"success": False, "error": "unknown_earn_id", "known": list(TOP10_EARN)}
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    today = _today()
    state = _load_state()
    users = state.setdefault("users", {})
    urec = users.setdefault(uid, {})
    day = urec.setdefault(today, {})
    if day.get(eid):
        return {"success": True, "duplicate": True, "earn_id": eid, "claimed_at": day[eid]}

    amt = float(amount if amount is not None else _DEFAULT_AMOUNTS.get(eid, 0.01))
    ref = f"game-earn:{eid}:{uid}:{today}"
    credited = credit_mn2(
        uid,
        amt,
        source=f"game_earn_{eid}",
        reference=ref,
        metadata={"earn_id": eid, **(metadata or {})},
    )
    if not credited.get("success") and not credited.get("duplicate"):
        return credited

    day[eid] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _save_state(state)
    return {
        "success": True,
        "earn_id": eid,
        "amount": amt,
        "user_id": uid,
        "duplicate": bool(credited.get("duplicate")),
        "credit": credited,
    }


def record_game_activity(user_id: str, game: str) -> Dict[str, Any]:
    """Track multi-game activity for streak/combo helpers."""
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}
    g = (game or "").strip().lower() or "unknown"
    today = _today()
    state = _load_state()
    users = state.setdefault("users", {})
    urec = users.setdefault(uid, {})
    day = urec.setdefault(today, {})
    games = set(day.get("games") or [])
    games.add(g)
    day["games"] = sorted(games)
    _save_state(state)
    bonuses: List[Dict[str, Any]] = []
    if len(games) >= 2 and not day.get("cross_game_combo"):
        bonuses.append(claim_earn(uid, "cross_game_combo", metadata={"games": list(games)}))
    if len(games) >= 3 and not day.get("daily_multi_game_streak"):
        bonuses.append(claim_earn(uid, "daily_multi_game_streak", metadata={"games": list(games)}))
    return {"success": True, "games": list(games), "bonuses": bonuses}


def monitor_check_in(user_id: str) -> Dict[str, Any]:
    return claim_earn(user_id, "monitor_check_in")


def first_win_of_day(user_id: str, *, game: str = "battle") -> Dict[str, Any]:
    record_game_activity(user_id, game)
    return claim_earn(user_id, "first_win_of_day", metadata={"game": game})
