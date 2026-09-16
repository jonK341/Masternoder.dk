"""Block Smiley Trophy — AI-style battle stats + arena rewards (plan 004)."""
from __future__ import annotations

import hashlib
import json
import os
import random
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "block_trophy_battle_config.json")
_CONFIG_LEGACY_PATH = os.path.join(_BASE, "data", "block_nft_battle_config.json")
_HISTORY_PATH = os.path.join(_BASE, "data", "block_trophy_battle_history.json")
_HISTORY_LEGACY_PATH = os.path.join(_BASE, "data", "block_nft_battle_history.json")
_COOLDOWN_PATH = os.path.join(_BASE, "data", "block_trophy_battle_cooldowns.json")
_COOLDOWN_LEGACY_PATH = os.path.join(_BASE, "data", "block_nft_battle_cooldowns.json")

RARITIES = ("common", "uncommon", "rare", "epic", "legendary")
SMILEY_MOODS = ("cheerful", "zen", "fierce", "lucky", "mischief", "stoic", "hyper")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with _LOCK:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        return True
    except Exception:
        return False


def _resolve_data_path(primary: str, legacy: str) -> str:
    if os.path.isfile(primary):
        return primary
    if os.path.isfile(legacy):
        return legacy
    return primary


def get_config() -> Dict[str, Any]:
    return _read_json(
        _resolve_data_path(_CONFIG_PATH, _CONFIG_LEGACY_PATH),
        {
            "enabled": True,
            "battles_per_edition_per_day": 12,
            "win_battle_points": 15,
            "loss_battle_points": 3,
            "draw_battle_points": 7,
            "win_game_points": 25,
            "loss_game_points": 5,
        },
    )


def _seed(edition_key: str, block_height: int) -> int:
    raw = f"block-smiley-nft-v1|{edition_key}|{block_height}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def serial_number(block_height: int, edition_no: int = 1) -> str:
    return f"BLK-{int(block_height):07d}-E{int(edition_no):04d}"


def generate_battle_stats(
    block_height: int,
    edition_key: str,
    *,
    edition_no: int = 1,
) -> Dict[str, Any]:
    """Deterministic AI-style battle stats from block height + edition."""
    h = int(block_height)
    rng = random.Random(_seed(edition_key, h))
    height_bonus = h % 23

    power = min(99, 35 + rng.randint(0, 45) + height_bonus)
    defense = min(99, 30 + rng.randint(0, 50) + (h % 11))
    speed = min(99, 25 + rng.randint(0, 55) + (h % 7))
    luck = min(99, 20 + rng.randint(0, 60))
    smile = min(100, 50 + rng.randint(0, 50))

    combat_rating = round(power * 0.4 + defense * 0.25 + speed * 0.2 + luck * 0.15, 1)
    rarity_roll = rng.random()
    if rarity_roll > 0.97:
        rarity = "legendary"
    elif rarity_roll > 0.88:
        rarity = "epic"
    elif rarity_roll > 0.72:
        rarity = "rare"
    elif rarity_roll > 0.45:
        rarity = "uncommon"
    else:
        rarity = "common"

    mood = SMILEY_MOODS[rng.randint(0, len(SMILEY_MOODS) - 1)]
    serial = serial_number(h, edition_no)

    return {
        "serial_number": serial,
        "block_height": h,
        "edition_key": edition_key,
        "edition_no": int(edition_no),
        "power": power,
        "defense": defense,
        "speed": speed,
        "luck": luck,
        "smile": smile,
        "combat_rating": combat_rating,
        "rarity": rarity,
        "mood": mood,
        "ai_generated": True,
        "trophy_kind": "block_smiley",
    }


def stats_for_edition(edition: Dict[str, Any]) -> Dict[str, Any]:
    """Return stored or freshly derived stats for an edition row."""
    if isinstance(edition.get("battle_stats"), dict) and edition["battle_stats"].get("power") is not None:
        return dict(edition["battle_stats"])

    block_height = edition.get("block_height")
    if block_height is None:
        iid = str(edition.get("item_id") or "")
        if iid.startswith("block-") and iid[6:].isdigit():
            block_height = int(iid[6:])

    if block_height is None:
        return {"error": "not_block_trophy"}

    return generate_battle_stats(
        int(block_height),
        str(edition.get("edition_key") or ""),
        edition_no=int(edition.get("edition_no") or 1),
    )


def _combat_score(stats: Dict[str, Any], rng: random.Random) -> float:
    return (
        float(stats.get("power") or 0) * 0.42
        + float(stats.get("defense") or 0) * 0.18
        + float(stats.get("speed") or 0) * 0.22
        + float(stats.get("luck") or 0) * 0.08
        + rng.randint(0, 20)
    )


def simulate_battle(attacker: Dict[str, Any], defender: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a single trophy battle round."""
    seed = _seed(
        str(attacker.get("edition_key") or "atk"),
        int(attacker.get("block_height") or 0),
    ) ^ _seed(str(defender.get("edition_key") or "def"), int(defender.get("block_height") or 0))
    rng = random.Random(seed)

    atk_score = _combat_score(attacker, rng)
    def_score = _combat_score(defender, rng)
    margin = atk_score - def_score

    if abs(margin) < 3:
        result = "draw"
    elif margin > 0:
        result = "win"
    else:
        result = "loss"

    return {
        "result": result,
        "attacker_score": round(atk_score, 2),
        "defender_score": round(def_score, 2),
        "margin": round(margin, 2),
        "attacker_stats": attacker,
        "defender_stats": defender,
    }


def _random_opponent_stats(block_height: int) -> Dict[str, Any]:
    """AI opponent smiley for unclaimed / mirror block heights."""
    h = max(1, int(block_height) + random.randint(-50, 50))
    ekey = f"TRO-block-{h}-shadow"
    return generate_battle_stats(h, ekey, edition_no=0)


def _cooldown_key(user_id: str, edition_key: str) -> str:
    return f"{user_id}:{edition_key}"


def _battles_today(user_id: str, edition_key: str) -> int:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = _read_json(_resolve_data_path(_COOLDOWN_PATH, _COOLDOWN_LEGACY_PATH), {"days": {}})
    row = (doc.get("days") or {}).get(day, {}).get(_cooldown_key(user_id, edition_key), 0)
    try:
        return int(row)
    except (TypeError, ValueError):
        return 0


def _increment_cooldown(user_id: str, edition_key: str) -> None:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _LOCK:
        doc = _read_json(_resolve_data_path(_COOLDOWN_PATH, _COOLDOWN_LEGACY_PATH), {"days": {}})
        days = doc.setdefault("days", {})
        day_row = days.setdefault(day, {})
        key = _cooldown_key(user_id, edition_key)
        day_row[key] = int(day_row.get(key) or 0) + 1
        doc["updated_at"] = _iso()
        _write_json(_COOLDOWN_PATH, doc)


def _append_history(entry: Dict[str, Any]) -> None:
    with _LOCK:
        doc = _read_json(_HISTORY_PATH, {"battles": []})
        battles = doc.setdefault("battles", [])
        battles.append(entry)
        doc["battles"] = battles[-500:]
        doc["updated_at"] = _iso()
        _write_json(_HISTORY_PATH, doc)


def _item_id_from_edition_key(edition_key: str) -> Optional[str]:
    ekey = (edition_key or "").strip()
    if not ekey.startswith("TRO-"):
        return None
    rest = ekey[4:]
    if "-" not in rest:
        return rest
    maybe_no = rest.rsplit("-", 1)[-1]
    if maybe_no.isdigit():
        return rest.rsplit("-", 1)[0]
    return rest


def _find_owned_edition(user_id: str, edition_key: str) -> Optional[Dict[str, Any]]:
    uid = (user_id or "").strip()
    ekey = (edition_key or "").strip()
    if not uid or not ekey:
        return None
    try:
        from backend.services.trophy_fulfillment_service import get_trophy_editions

        item_id = _item_id_from_edition_key(ekey)
        candidates = get_trophy_editions(uid, item_id) if item_id else get_trophy_editions(uid)
        for ed in candidates:
            if (ed.get("edition_key") or "") == ekey:
                return ed
    except Exception:
        pass
    return None


def battle_with_trophy(user_id: str, edition_key: str) -> Dict[str, Any]:
    """Battle using an owned Block Smiley Trophy edition; award unified points."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "battle_disabled"}

    uid = (user_id or "").strip()
    ekey = (edition_key or "").strip()
    if not uid or uid in ("default_user", "guest"):
        return {"success": False, "error": "guest_blocked"}
    if not ekey:
        return {"success": False, "error": "edition_key_required"}

    edition = _find_owned_edition(uid, ekey)
    if not edition:
        return {"success": False, "error": "edition_not_owned", "edition_key": ekey}

    limit = int(cfg.get("battles_per_edition_per_day") or 12)
    used = _battles_today(uid, ekey)
    if used >= limit:
        return {
            "success": False,
            "error": "daily_battle_limit",
            "battles_today": used,
            "limit": limit,
        }

    attacker = stats_for_edition(edition)
    if attacker.get("error"):
        return {"success": False, "error": attacker["error"]}

    block_height = int(attacker.get("block_height") or edition.get("block_height") or 0)
    defender = _random_opponent_stats(block_height)
    outcome = simulate_battle(attacker, defender)
    result = outcome["result"]

    bp_delta = {
        "win": int(cfg.get("win_battle_points") or 15),
        "loss": int(cfg.get("loss_battle_points") or 3),
        "draw": int(cfg.get("draw_battle_points") or 7),
    }.get(result, 0)
    gp_delta = {
        "win": int(cfg.get("win_game_points") or 25),
        "loss": int(cfg.get("loss_game_points") or 5),
        "draw": int(cfg.get("draw_battle_points") or 7),
    }.get(result, 0)

    rewards: Dict[str, Any] = {"battle_points": bp_delta, "game_points": gp_delta}
    try:
        from backend.services.unified_points_database import unified_points_db

        meta = {
            "edition_key": ekey,
            "block_height": block_height,
            "serial_number": attacker.get("serial_number"),
            "battle_result": result,
            "trophy_kind": "block_smiley",
        }
        if bp_delta:
            unified_points_db.add_points(uid, "battle_points", float(bp_delta), "block_trophy_battle", meta)
        if gp_delta:
            unified_points_db.add_points(uid, "game_points", float(gp_delta), "block_trophy_battle", meta)
        if result == "win":
            unified_points_db.add_points(uid, "battle_wins", 1, "block_trophy_battle", meta)
    except Exception:
        pass

    _increment_cooldown(uid, ekey)
    battle_id = hashlib.sha256(f"{ekey}:{_iso()}:{outcome['margin']}".encode()).hexdigest()[:12]
    record = {
        "battle_id": battle_id,
        "user_id": uid,
        "edition_key": ekey,
        "serial_number": attacker.get("serial_number"),
        "result": result,
        "rewards": rewards,
        "outcome": outcome,
        "fought_at": _iso(),
    }
    _append_history(record)

    return {
        "success": True,
        "battle_id": battle_id,
        "result": result,
        "rewards": rewards,
        "attacker": attacker,
        "defender": defender,
        "scores": {
            "attacker": outcome["attacker_score"],
            "defender": outcome["defender_score"],
            "margin": outcome["margin"],
        },
        "battles_today": used + 1,
        "battles_limit": limit,
        "message": _battle_message(result, attacker, defender),
    }


def _battle_message(result: str, attacker: Dict[str, Any], defender: Dict[str, Any]) -> str:
    serial = attacker.get("serial_number") or "your smiley"
    opp = defender.get("serial_number") or "rival smiley"
    if result == "win":
        return f"{serial} defeated {opp} in the arena!"
    if result == "loss":
        return f"{serial} was out-smiled by {opp}."
    return f"{serial} and {opp} grinned to a draw."


def battle_history(user_id: str, *, limit: int = 20) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    doc = _read_json(_resolve_data_path(_HISTORY_PATH, _HISTORY_LEGACY_PATH), {"battles": []})
    rows = [b for b in (doc.get("battles") or []) if isinstance(b, dict) and b.get("user_id") == uid]
    rows = list(reversed(rows))[: max(1, min(limit, 100))]
    return {"success": True, "user_id": uid, "battles": rows, "count": len(rows)}
