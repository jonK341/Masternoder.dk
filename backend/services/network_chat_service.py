"""
Network chat for wallet — JSONL message store, presence heartbeat stub, ratings, micro MN2 rewards.
"""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "network_chat_config.json")
_MESSAGES_PATH = os.path.join(_BASE, "data", "network_chat_messages.jsonl")
_PRESENCE_PATH = os.path.join(_BASE, "data", "network_chat_presence.json")
_REWARDS_STATE_PATH = os.path.join(_BASE, "data", "network_chat_rewards_state.json")
_GUEST_IDS = frozenset({"", "default_user", "guest"})


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def get_config() -> Dict[str, Any]:
    cfg = _read_json(_CONFIG_PATH)
    if not cfg:
        cfg = {"enabled": False, "rewards": {}}
    return cfg


def _load_rewards_state() -> dict:
    with _LOCK:
        return _read_json(_REWARDS_STATE_PATH)


def _save_rewards_state(data: dict) -> None:
    with _LOCK:
        _write_json(_REWARDS_STATE_PATH, data)


def _user_day_rec(state: dict, user_id: str, day: str) -> dict:
    users = state.setdefault("users", {})
    rec = users.setdefault(user_id, {})
    days = rec.setdefault("days", {})
    return days.setdefault(day, {"total_mn2": 0.0, "messages": 0, "ratings": 0, "heartbeats": 0})


def _parse_ts(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except Exception:
        return None


def _load_presence() -> dict:
    with _LOCK:
        return _read_json(_PRESENCE_PATH)


def _save_presence(data: dict) -> None:
    with _LOCK:
        _write_json(_PRESENCE_PATH, data)


def _read_messages(limit: int = 50) -> List[Dict[str, Any]]:
    if not os.path.isfile(_MESSAGES_PATH):
        return []
    lines: List[Dict[str, Any]] = []
    try:
        with open(_MESSAGES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        lines.append(row)
                except Exception:
                    continue
    except Exception:
        return []
    return lines[-limit:]


def _append_message(row: dict) -> None:
    os.makedirs(os.path.dirname(_MESSAGES_PATH), exist_ok=True)
    with _LOCK:
        with open(_MESSAGES_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _online_users(cfg: dict) -> List[Dict[str, Any]]:
    ttl = int(cfg.get("presence_ttl_seconds") or 120)
    now = datetime.now(timezone.utc)
    presence = _load_presence().get("users") or {}
    online: List[Dict[str, Any]] = []
    for uid, rec in presence.items():
        if not isinstance(rec, dict):
            continue
        last = _parse_ts(rec.get("last_seen"))
        if last and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last and (now - last).total_seconds() <= ttl:
            online.append({
                "user_id": uid,
                "display_name": rec.get("display_name") or uid,
                "status": rec.get("status") or "online",
                "last_seen": rec.get("last_seen"),
            })
    stub = cfg.get("stub_online_users") or []
    seen = {u["user_id"] for u in online}
    for s in stub:
        if isinstance(s, dict) and s.get("user_id") not in seen:
            online.append(s)
    return online


def _credit_reward(user_id: str, amount: float, kind: str, reference: str) -> Dict[str, Any]:
    if amount <= 0:
        return {"success": True, "mn2_awarded": 0.0}
    try:
        from backend.services.game_mn2_rewards import credit_mn2
        return credit_mn2(
            user_id,
            amount,
            source="network_chat",
            reference=reference,
            metadata={"kind": kind, "day": _today()},
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _try_reward(user_id: str, kind: str) -> Dict[str, Any]:
    """Apply per-kind caps from network_chat_config rewards block."""
    if user_id in _GUEST_IDS:
        return {"success": False, "error": "guest", "mn2_awarded": 0.0}

    cfg = get_config()
    rewards = cfg.get("rewards") if isinstance(cfg.get("rewards"), dict) else {}
    day = _today()
    state = _load_rewards_state()
    day_rec = _user_day_rec(state, user_id, day)
    global_cap = float(rewards.get("global_daily_cap_mn2") or 0.02)
    earned = float(day_rec.get("total_mn2") or 0)
    if earned >= global_cap - 1e-12:
        return {"success": False, "error": "global_cap", "mn2_awarded": 0.0}

    amount = 0.0
    if kind == "message":
        max_n = int(rewards.get("max_messages_rewarded_per_day") or 20)
        if int(day_rec.get("messages") or 0) >= max_n:
            return {"success": False, "error": "message_cap", "mn2_awarded": 0.0}
        cap = float(rewards.get("message_daily_cap_mn2") or 0.01)
        if float(day_rec.get("message_mn2") or 0) >= cap - 1e-12:
            return {"success": False, "error": "message_cap", "mn2_awarded": 0.0}
        amount = float(rewards.get("message_post_mn2") or 0.001)
        day_rec["messages"] = int(day_rec.get("messages") or 0) + 1
        day_rec["message_mn2"] = round(float(day_rec.get("message_mn2") or 0) + amount, 8)
    elif kind == "rating":
        max_n = int(rewards.get("max_ratings_rewarded_per_day") or 15)
        if int(day_rec.get("ratings") or 0) >= max_n:
            return {"success": False, "error": "rating_cap", "mn2_awarded": 0.0}
        cap = float(rewards.get("rating_daily_cap_mn2") or 0.005)
        if float(day_rec.get("rating_mn2") or 0) >= cap - 1e-12:
            return {"success": False, "error": "rating_cap", "mn2_awarded": 0.0}
        amount = float(rewards.get("rating_given_mn2") or 0.0005)
        day_rec["ratings"] = int(day_rec.get("ratings") or 0) + 1
        day_rec["rating_mn2"] = round(float(day_rec.get("rating_mn2") or 0) + amount, 8)
    elif kind == "heartbeat":
        max_n = int(rewards.get("max_heartbeats_rewarded_per_day") or 24)
        if int(day_rec.get("heartbeats") or 0) >= max_n:
            return {"success": False, "error": "heartbeat_cap", "mn2_awarded": 0.0}
        cap = float(rewards.get("heartbeat_daily_cap_mn2") or 0.006)
        if float(day_rec.get("heartbeat_mn2") or 0) >= cap - 1e-12:
            return {"success": False, "error": "heartbeat_cap", "mn2_awarded": 0.0}
        cooldown = int(rewards.get("heartbeat_cooldown_seconds") or 60)
        last = day_rec.get("last_heartbeat_at")
        last_dt = _parse_ts(last)
        if last_dt:
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
            if elapsed < cooldown:
                return {
                    "success": False,
                    "error": "cooldown",
                    "cooldown_remaining_sec": int(cooldown - elapsed),
                    "mn2_awarded": 0.0,
                }
        amount = float(rewards.get("heartbeat_mn2") or 0.0003)
        day_rec["heartbeats"] = int(day_rec.get("heartbeats") or 0) + 1
        day_rec["heartbeat_mn2"] = round(float(day_rec.get("heartbeat_mn2") or 0) + amount, 8)
        day_rec["last_heartbeat_at"] = _iso()
    else:
        return {"success": False, "error": "unknown_kind", "mn2_awarded": 0.0}

    room = max(0.0, global_cap - earned)
    amount = round(min(amount, room), 8)
    if amount <= 0:
        return {"success": False, "error": "cap_exhausted", "mn2_awarded": 0.0}

    ref = f"network-chat:{kind}:{user_id}:{day}:{uuid.uuid4().hex[:8]}"
    credit = _credit_reward(user_id, amount, kind, ref)
    if not credit.get("success"):
        return credit

    day_rec["total_mn2"] = round(earned + amount, 8)
    state["users"][user_id]["days"][day] = day_rec
    _save_rewards_state(state)
    return {"success": True, "mn2_awarded": amount, "earned_today_mn2": day_rec["total_mn2"]}


def get_status(user_id: str, limit: int = 50) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    guest = user_id in _GUEST_IDS
    cfg = get_config()
    limit = max(1, min(int(limit or 50), 100))
    day = _today()
    state = _load_rewards_state()
    day_rec = _user_day_rec(state, user_id, day) if not guest else {}
    rewards = cfg.get("rewards") if isinstance(cfg.get("rewards"), dict) else {}

    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "user_id": user_id,
        "guest": guest,
        "room_id": cfg.get("room_id") or "wallet-network",
        "online_count": len(_online_users(cfg)),
        "online_users": _online_users(cfg),
        "messages": _read_messages(limit),
        "message_count": len(_read_messages(1000)),
        "engagement_disclaimer": cfg.get("engagement_disclaimer"),
        "rewards": {
            "earned_today_mn2": round(float(day_rec.get("total_mn2") or 0), 8),
            "global_daily_cap_mn2": float(rewards.get("global_daily_cap_mn2") or 0.02),
            "message_post_mn2": float(rewards.get("message_post_mn2") or 0.001),
            "rating_given_mn2": float(rewards.get("rating_given_mn2") or 0.0005),
            "heartbeat_mn2": float(rewards.get("heartbeat_mn2") or 0.0003),
        },
        "message": "Sign in to chat and earn micro MN2." if guest else None,
    }


def heartbeat(user_id: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    if user_id in _GUEST_IDS:
        return {"success": False, "error": "guest", "message": "Sign in for presence."}

    presence = _load_presence()
    users = presence.setdefault("users", {})
    users[user_id] = {
        "display_name": (display_name or user_id)[:64],
        "status": "online",
        "last_seen": _iso(),
    }
    _save_presence(presence)
    reward = _try_reward(user_id, "heartbeat")
    return {
        "success": True,
        "user_id": user_id,
        "last_seen": users[user_id]["last_seen"],
        "reward": reward,
    }


def post_message(user_id: str, text: str, display_name: Optional[str] = None) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    if user_id in _GUEST_IDS:
        return {"success": False, "error": "guest", "message": "Sign in to post messages."}

    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "chat_disabled"}

    text = (text or "").strip()
    max_len = int(cfg.get("max_message_length") or 500)
    if not text:
        return {"success": False, "error": "empty_message"}
    if len(text) > max_len:
        return {"success": False, "error": "message_too_long", "max_length": max_len}

    msg_id = f"nc-{uuid.uuid4().hex[:12]}"
    row = {
        "id": msg_id,
        "user_id": user_id,
        "display_name": (display_name or user_id)[:64],
        "text": text,
        "created_at": _iso(),
        "ratings": [],
        "rating_avg": 0.0,
        "rating_count": 0,
    }
    _append_message(row)
    heartbeat(user_id, display_name)
    reward = _try_reward(user_id, "message")
    return {"success": True, "message": row, "reward": reward}


def post_rating(user_id: str, message_id: str, stars: int) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    if user_id in _GUEST_IDS:
        return {"success": False, "error": "guest", "message": "Sign in to rate messages."}

    try:
        stars = int(stars)
    except (TypeError, ValueError):
        stars = 0
    if stars < 1 or stars > 5:
        return {"success": False, "error": "invalid_stars", "message": "Stars must be 1-5."}

    message_id = (message_id or "").strip()
    if not message_id:
        return {"success": False, "error": "missing_message_id"}

    if not os.path.isfile(_MESSAGES_PATH):
        return {"success": False, "error": "message_not_found"}

    updated = None
    new_lines: List[str] = []
    found = False
    with _LOCK:
        with open(_MESSAGES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    new_lines.append(line)
                    continue
                if isinstance(row, dict) and row.get("id") == message_id:
                    found = True
                    ratings = row.get("ratings") if isinstance(row.get("ratings"), list) else []
                    ratings.append({
                        "user_id": user_id,
                        "stars": stars,
                        "created_at": _iso(),
                    })
                    row["ratings"] = ratings[-50:]
                    row["rating_count"] = len(row["ratings"])
                    row["rating_avg"] = round(
                        sum(r.get("stars", 0) for r in row["ratings"] if isinstance(r, dict)) / max(1, len(row["ratings"])),
                        2,
                    )
                    updated = row
                    new_lines.append(json.dumps(row, ensure_ascii=False))
                else:
                    new_lines.append(line)
        if found:
            tmp = _MESSAGES_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                for ln in new_lines:
                    f.write(ln + "\n")
            os.replace(tmp, _MESSAGES_PATH)

    if not found:
        return {"success": False, "error": "message_not_found"}

    reward = _try_reward(user_id, "rating")
    return {"success": True, "message": updated, "reward": reward}
