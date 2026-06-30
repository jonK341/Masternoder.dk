"""Crash crew mode — friends share one bust point, cash out individually (Wave 3)."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.services import casino_service as cs


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _config() -> Dict[str, Any]:
    cfg = cs._load_config()
    block = cfg.get("crash_crew") if isinstance(cfg.get("crash_crew"), dict) else {}
    crash = cs._crash_config()
    return {
        "enabled": bool(block.get("enabled", True)),
        "lobby_seconds": int(block.get("lobby_seconds") or 30),
        "min_players": int(block.get("min_players") or 2),
        "max_players": int(block.get("max_players") or 6),
        "house_edge": crash["house_edge"],
        "growth_per_second": crash["growth_per_second"],
        "max_round_seconds": crash["max_round_seconds"],
        "max_auto_cashout": crash["max_auto_cashout"],
    }


def _rooms_path() -> str:
    log_dir = cs._log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_crash_crew.json")


def _load() -> Dict[str, Any]:
    path = _rooms_path()
    if not os.path.isfile(path):
        return {"rooms": {}}
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("rooms", {})
            return data
    except Exception:
        pass
    return {"rooms": {}}


def _save(data: Dict[str, Any]) -> None:
    import json
    try:
        with open(_rooms_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _room_public(room: Dict[str, Any]) -> Dict[str, Any]:
    members = room.get("members") or {}
    return {
        "room_id": room.get("room_id"),
        "host": room.get("host"),
        "status": room.get("status"),
        "bet": room.get("bet"),
        "currency": room.get("currency"),
        "member_count": len(members),
        "max_players": room.get("max_players"),
        "lobby_ends_at": room.get("lobby_ends_at"),
        "started_at": room.get("started_at"),
        "bust": room.get("bust") if room.get("status") == "live" else None,
        "members": [
            {
                "user_id": uid,
                "cashed_out": m.get("cashed_out"),
                "cashout": m.get("cashout"),
                "settled": m.get("settled"),
            }
            for uid, m in members.items()
        ],
        "fairness": room.get("fairness") if room.get("status") in ("live", "settled") else None,
    }


def _expire_rooms(data: Dict[str, Any]) -> None:
    conf = _config()
    now = _utcnow()
    for rid, room in list((data.get("rooms") or {}).items()):
        if not isinstance(room, dict):
            data["rooms"].pop(rid, None)
            continue
        status = room.get("status")
        if status == "lobby":
            try:
                end = datetime.fromisoformat(str(room.get("lobby_ends_at")).replace("Z", "+00:00"))
            except Exception:
                end = now
            if now >= end:
                if len(room.get("members") or {}) >= conf["min_players"]:
                    _launch_room(room, conf)
                else:
                    room["status"] = "cancelled"
        elif status == "live":
            try:
                started = datetime.fromisoformat(str(room.get("started_at")).replace("Z", "+00:00"))
            except Exception:
                started = now
            grace = conf["max_round_seconds"] + 10
            if (now - started).total_seconds() > grace:
                _auto_settle_room(room, conf)
                room["status"] = "settled"


def _launch_room(room: Dict[str, Any], conf: Dict[str, Any]) -> None:
    from backend.services import casino_rng
    from backend.services.engines import crash as crash_engine

    host = room.get("host") or "house"
    members = room.get("members") or {}
    currency = cs._normalize_currency(room.get("currency"))
    bet = cs._parse_bet_amount(room.get("bet"), currency) or 0

    for uid in list(members.keys()):
        err = cs._validate_bet(uid, bet, currency)
        if err:
            members.pop(uid, None)
            continue
        cs._apply_balance_delta(uid, -bet, currency, "crash_crew", {"phase": "stake", "room_id": room.get("room_id")})

    if len(members) < conf["min_players"]:
        room["status"] = "cancelled"
        return

    proof = casino_rng.draw(host)
    bust = crash_engine.crash_point(proof["float"], conf["house_edge"])
    room["status"] = "live"
    room["started_at"] = _iso()
    room["bust"] = bust
    room["growth_per_second"] = conf["growth_per_second"]
    room["fairness"] = {
        "server_seed_hash": proof["server_seed_hash"],
        "client_seed": proof["client_seed"],
        "nonce": proof["nonce"],
        "shared_bust": bust,
    }
    room["members"] = members


def _member_elapsed(room: Dict[str, Any]) -> float:
    try:
        started = datetime.fromisoformat(str(room.get("started_at")).replace("Z", "+00:00"))
    except Exception:
        return 0.0
    return max(0.0, (_utcnow() - started).total_seconds())


def _settle_member(room: Dict[str, Any], user_id: str, *, multiplier: Optional[float] = None) -> Dict[str, Any]:
    from backend.services.engines import crash as crash_engine

    members = room.get("members") or {}
    member = members.get(user_id)
    if not isinstance(member, dict):
        return {"success": False, "error": "not_in_room"}
    if member.get("settled"):
        return {"success": False, "error": "already_settled"}
    if room.get("status") != "live":
        return {"success": False, "error": "round_not_live"}

    currency = cs._normalize_currency(room.get("currency"))
    bet = cs._parse_bet_amount(room.get("bet"), currency) or 0
    growth = float(room.get("growth_per_second") or 0.13863)
    outcome_calc = crash_engine.settle(
        bust=float(room.get("bust") or 1.0),
        elapsed_seconds=_member_elapsed(room),
        requested_multiplier=multiplier,
        auto_cashout=member.get("auto_cashout"),
        growth_per_second=growth,
    )
    if outcome_calc["won"]:
        payout = bet * outcome_calc["multiplier"]
        outcome = "win"
        cashout = outcome_calc["cashout"]
    else:
        payout = 0.0
        outcome = "loss"
        cashout = 0.0

    member["cashed_out"] = True
    member["cashout"] = cashout
    member["settled"] = True
    result = cs.record_crash_crew_settlement(
        user_id,
        bet=bet,
        currency=currency,
        bust=float(room.get("bust") or 1.0),
        cashout=cashout,
        payout=payout,
        outcome=outcome,
        fairness=room.get("fairness") or {},
        growth_per_second=growth,
        crew_room_id=str(room.get("room_id") or ""),
    )
    result["crew"] = _room_public(room)
    return result


def _auto_settle_room(room: Dict[str, Any], conf: Dict[str, Any]) -> None:
    for uid, member in list((room.get("members") or {}).items()):
        if isinstance(member, dict) and not member.get("settled"):
            _settle_member(room, uid, multiplier=None)


def list_open_rooms(limit: int = 12) -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": False, "error": "crash_crew_disabled"}
    data = _load()
    _expire_rooms(data)
    _save(data)
    rows = []
    for room in (data.get("rooms") or {}).values():
        if isinstance(room, dict) and room.get("status") in ("lobby", "live"):
            rows.append(_room_public(room))
    rows.sort(key=lambda r: r.get("lobby_ends_at") or r.get("started_at") or "", reverse=True)
    return {"success": True, "rooms": rows[:limit], "config": conf}


def create_room(
    user_id: str,
    bet: float,
    currency: str = "coins",
    *,
    max_players: Optional[int] = None,
) -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": False, "error": "crash_crew_disabled"}
    user_id = (user_id or "").strip()
    if not user_id:
        return {"success": False, "error": "user_id_required"}
    currency = cs._normalize_currency(currency)
    err = cs._validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = cs._parse_bet_amount(bet, currency) or 0

    data = _load()
    _expire_rooms(data)
    for room in (data.get("rooms") or {}).values():
        if isinstance(room, dict) and user_id in (room.get("members") or {}) and room.get("status") in ("lobby", "live"):
            return {"success": False, "error": "already_in_crew_room", "room_id": room.get("room_id")}

    room_id = f"crew_{uuid.uuid4().hex[:10]}"
    cap = min(conf["max_players"], max(conf["min_players"], int(max_players or conf["max_players"])))
    lobby_end = _utcnow() + timedelta(seconds=conf["lobby_seconds"])
    room = {
        "room_id": room_id,
        "host": user_id,
        "status": "lobby",
        "bet": amount,
        "currency": currency,
        "max_players": cap,
        "lobby_ends_at": lobby_end.isoformat().replace("+00:00", "Z"),
        "started_at": None,
        "bust": None,
        "members": {
            user_id: {"joined_at": _iso(), "auto_cashout": None, "cashed_out": False, "cashout": None, "settled": False},
        },
    }
    data.setdefault("rooms", {})[room_id] = room
    _save(data)
    return {"success": True, "room": _room_public(room), "config": conf}


def join_room(
    user_id: str,
    room_id: str,
    *,
    auto_cashout: Optional[float] = None,
) -> Dict[str, Any]:
    conf = _config()
    user_id = (user_id or "").strip()
    room_id = (room_id or "").strip()
    data = _load()
    _expire_rooms(data)
    room = (data.get("rooms") or {}).get(room_id)
    if not isinstance(room, dict):
        _save(data)
        return {"success": False, "error": "room_not_found"}
    if room.get("status") != "lobby":
        _save(data)
        return {"success": False, "error": "lobby_closed"}
    members = room.setdefault("members", {})
    if user_id in members:
        _save(data)
        return {"success": True, "room": _room_public(room)}
    if len(members) >= int(room.get("max_players") or conf["max_players"]):
        _save(data)
        return {"success": False, "error": "room_full"}
    err = cs._validate_bet(user_id, room.get("bet"), room.get("currency"))
    if err:
        _save(data)
        return {"success": False, "error": err}
    auto = None
    if auto_cashout is not None:
        try:
            auto = max(1.01, min(float(auto_cashout), conf["max_auto_cashout"]))
        except (TypeError, ValueError):
            auto = None
    members[user_id] = {
        "joined_at": _iso(),
        "auto_cashout": auto,
        "cashed_out": False,
        "cashout": None,
        "settled": False,
    }
    _save(data)
    return {"success": True, "room": _room_public(room)}


def launch_room(user_id: str, room_id: str) -> Dict[str, Any]:
    conf = _config()
    data = _load()
    _expire_rooms(data)
    room = (data.get("rooms") or {}).get(room_id)
    if not isinstance(room, dict):
        _save(data)
        return {"success": False, "error": "room_not_found"}
    if room.get("host") != user_id:
        _save(data)
        return {"success": False, "error": "host_only"}
    if room.get("status") != "lobby":
        _save(data)
        return {"success": False, "error": "lobby_closed"}
    if len(room.get("members") or {}) < conf["min_players"]:
        _save(data)
        return {"success": False, "error": "need_more_players", "min_players": conf["min_players"]}
    _launch_room(room, conf)
    _save(data)
    return {"success": room.get("status") == "live", "room": _room_public(room)}


def get_room(room_id: str) -> Dict[str, Any]:
    data = _load()
    _expire_rooms(data)
    _save(data)
    room = (data.get("rooms") or {}).get((room_id or "").strip())
    if not isinstance(room, dict):
        return {"success": False, "error": "room_not_found"}
    return {"success": True, "room": _room_public(room)}


def cashout(user_id: str, room_id: str, *, multiplier: Optional[float] = None) -> Dict[str, Any]:
    data = _load()
    room = (data.get("rooms") or {}).get((room_id or "").strip())
    if not isinstance(room, dict):
        return {"success": False, "error": "room_not_found"}
    result = _settle_member(room, user_id, multiplier=multiplier)
    if all(m.get("settled") for m in (room.get("members") or {}).values()):
        room["status"] = "settled"
    _save(data)
    return result
