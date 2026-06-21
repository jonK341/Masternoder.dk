"""
Star Map Routes
API for 7 nearest stars, planets, life-bearing b. Used by hunters/trophies game and agent specials.
Star Map 25: 25 WH40K-themed investigation points; investigate to earn game_points.
"""
import os
import json
from flask import Blueprint, jsonify, request

star_map_bp = Blueprint("star_map", __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAR_MAP_PATH = os.path.join(BASE_DIR, "data", "star_map.json")
STAR_MAP_25_PATH = os.path.join(BASE_DIR, "data", "star_map_25.json")
STAR_MAP_25_INVESTIGATIONS_PATH = os.path.join(BASE_DIR, "data", "star_map_25_investigations.json")
STAR_MAP_25_BUILDINGS_PATH = os.path.join(BASE_DIR, "data", "starmap25_buildings.json")
STAR_MAP_25_UNITS_PATH = os.path.join(BASE_DIR, "data", "starmap25_units.json")
STAR_MAP_25_BUILDUP_PATH = os.path.join(BASE_DIR, "data", "starmap25_buildup.json")
STAR_MAP_25_INVASIONS_PATH = os.path.join(BASE_DIR, "data", "starmap25_invasions.json")
STAR_MAP_25_EVENTS_PATH = os.path.join(BASE_DIR, "data", "starmap25_events.json")
STAR_MAP_25_TROPHIES_PATH = os.path.join(BASE_DIR, "data", "starmap25_trophies.json")
STAR_MAP_25_CRYPTO_PATH = os.path.join(BASE_DIR, "data", "starmap25_crypto.json")
STAR_MAP_25_LEVELS_PATH = os.path.join(BASE_DIR, "data", "starmap25_system_levels.json")
STAR_MAP_25_WALKTHROUGH_PATH = os.path.join(BASE_DIR, "data", "starmap25_walkthrough.json")
STAR_MAP_25_AI_PROOF_DOCS_PATH = os.path.join(BASE_DIR, "data", "starmap25_ai_proof_docs.json")
AGENT_CALENDAR_PATH = os.path.join(BASE_DIR, "data", "agent_calendar.json")
STAR_MAP_25_EVENT_LOG_PATH = os.path.join(BASE_DIR, "logs", "starmap25_events.jsonl")

# Season 2+: investigation rewards scale base JSON point_value (display + awards stay aligned)
STAR_MAP_INVESTIGATION_MULTIPLIER = 1.2


def _sm25_investigation_reward(base) -> float:
    """Scaled reward for Star Map 25 investigations (matches status totals)."""
    try:
        return round(float(base) * STAR_MAP_INVESTIGATION_MULTIPLIER, 2)
    except (TypeError, ValueError):
        return round(10.0 * STAR_MAP_INVESTIGATION_MULTIPLIER, 2)


def _get_points_snapshot(user_id: str):
    try:
        from backend.services.unified_points_database import unified_points_db
        result = unified_points_db.get_all_points(user_id) or {}
        if result.get("success") and isinstance(result.get("points"), dict):
            return result["points"]
    except Exception:
        pass
    return {}


def _active_starmap25_boosters(user_id: str):
    points = _get_points_snapshot(user_id)
    boosters = points.get("active_boosters") or []
    active = []
    for booster in boosters:
        text = ((booster.get("id") or "") + " " + (booster.get("name") or "")).lower()
        if "star map 25" in text or "starmap25" in text or "star-map-25" in text:
            active.append(booster)
    return active


def _starmap25_booster_multiplier(user_id: str) -> float:
    return 2.0 if _active_starmap25_boosters(user_id) else 1.0


def _utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _parse_iso_utc(value):
    if not value:
        return None
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _seconds_until(iso_value):
    dt = _parse_iso_utc(iso_value)
    if not dt:
        return 0
    return max(0, int((dt - _utc_now()).total_seconds()))


def _load_star_map():
    if os.path.exists(STAR_MAP_PATH):
        with open(STAR_MAP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"name": "Star Map", "stars": [], "specials": ["run_verification", "run_dna_test", "view_star_map"]}


def _load_star_map_25():
    if os.path.exists(STAR_MAP_25_PATH):
        with open(STAR_MAP_25_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        metadata = data.get("point_metadata", {})
        if metadata:
            points = []
            for point in data.get("points", []):
                enriched = dict(point)
                enriched.update(metadata.get(point.get("id"), {}))
                points.append(enriched)
            data["points"] = points
        return data
    return {"name": "Star Map 25", "points": [], "specials": ["run_verification", "run_dna_test", "view_star_map"]}


def _load_investigations():
    if os.path.exists(STAR_MAP_25_INVESTIGATIONS_PATH):
        try:
            with open(STAR_MAP_25_INVESTIGATIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_investigations(data):
    try:
        os.makedirs(os.path.dirname(STAR_MAP_25_INVESTIGATIONS_PATH), exist_ok=True)
        with open(STAR_MAP_25_INVESTIGATIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _load_invasions():
    if os.path.exists(STAR_MAP_25_INVASIONS_PATH):
        try:
            with open(STAR_MAP_25_INVASIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}


def _save_invasions(data):
    try:
        os.makedirs(os.path.dirname(STAR_MAP_25_INVASIONS_PATH), exist_ok=True)
        with open(STAR_MAP_25_INVASIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _load_trophy_awards():
    if os.path.exists(STAR_MAP_25_TROPHIES_PATH):
        try:
            with open(STAR_MAP_25_TROPHIES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}


def _save_trophy_awards(data):
    try:
        os.makedirs(os.path.dirname(STAR_MAP_25_TROPHIES_PATH), exist_ok=True)
        with open(STAR_MAP_25_TROPHIES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _load_crypto_state():
    if os.path.exists(STAR_MAP_25_CRYPTO_PATH):
        try:
            with open(STAR_MAP_25_CRYPTO_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}


def _save_crypto_state(data):
    try:
        os.makedirs(os.path.dirname(STAR_MAP_25_CRYPTO_PATH), exist_ok=True)
        with open(STAR_MAP_25_CRYPTO_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _starmap25_crypto_options():
    return [
        {
            "id": "cartographer_hash",
            "name": "Cartographer Hash",
            "description": "Convert fresh investigation telemetry into a small MN2 reward.",
            "cooldown_sec": 30 * 60,
            "base_mn2": 0.0025,
            "requires": {"investigated": 1},
        },
        {
            "id": "buildup_yield",
            "name": "Buildup Yield",
            "description": "Mine logistical yield from buildings and deployed units.",
            "cooldown_sec": 2 * 60 * 60,
            "base_mn2": 0.004,
            "requires": {"placements": 1},
        },
        {
            "id": "secured_relay",
            "name": "Secured Relay",
            "description": "Claim a stronger reward from systems you have secured with invasions.",
            "cooldown_sec": 4 * 60 * 60,
            "base_mn2": 0.008,
            "requires": {"secured": 1},
        },
        {
            "id": "segmentum_route",
            "name": "Segmentum Route",
            "description": "Run a long-haul Segmentum trade route after broader map progress.",
            "cooldown_sec": 12 * 60 * 60,
            "base_mn2": 0.015,
            "requires": {"investigated": 5},
        },
    ]


def _starmap25_crypto_progress(user_id: str):
    inv = _load_investigations()
    investigated = inv.get(user_id, [])
    invasions = _load_invasions()
    invaded = invasions.get("users", {}).get(user_id, {}).get("invaded_ids", [])
    buildup = _load_buildup()
    placements = buildup.get("users", {}).get(user_id, {}).get("placements", [])
    levels = _get_user_system_levels(user_id)
    max_level = int(_load_system_levels_config().get("max_level", 5) or 5)
    return {
        "investigated": len(investigated),
        "secured": len(invaded),
        "placements": len(placements),
        "max_level_systems": sum(1 for v in levels.values() if int(v or 0) >= max_level),
        "pending_buildup_points": _compute_pending_buildup_points(user_id),
    }


def _crypto_requirement_met(option, progress):
    for key, needed in (option.get("requires") or {}).items():
        if float(progress.get(key, 0) or 0) < float(needed or 0):
            return False
    return True


def _crypto_reward_amount(option, progress):
    amount = float(option.get("base_mn2", 0) or 0)
    if option["id"] == "cartographer_hash":
        amount += min(float(progress.get("investigated", 0) or 0), 25) * 0.00015
    elif option["id"] == "buildup_yield":
        amount += min(float(progress.get("placements", 0) or 0), 40) * 0.0002
        amount += min(float(progress.get("pending_buildup_points", 0) or 0), 500) * 0.000002
    elif option["id"] == "secured_relay":
        amount += min(float(progress.get("secured", 0) or 0), 25) * 0.0005
    elif option["id"] == "segmentum_route":
        amount += min(float(progress.get("max_level_systems", 0) or 0), 25) * 0.0004
    return round(amount, 8)


def _starmap25_crypto_status(user_id: str):
    state = _load_crypto_state()
    user_state = state.setdefault("users", {}).setdefault(user_id, {
        "total_mn2_earned": 0,
        "claims": [],
        "options": {},
    })
    progress = _starmap25_crypto_progress(user_id)
    options = []
    for option in _starmap25_crypto_options():
        option_state = user_state.setdefault("options", {}).setdefault(option["id"], {})
        remaining = _seconds_until(option_state.get("next_claim_at"))
        unlocked = _crypto_requirement_met(option, progress)
        options.append({
            **option,
            "reward_mn2": _crypto_reward_amount(option, progress),
            "unlocked": unlocked,
            "ready": unlocked and remaining <= 0,
            "cooldown_remaining_sec": remaining,
            "last_claim_at": option_state.get("last_claim_at"),
            "next_claim_at": option_state.get("next_claim_at"),
            "claims_count": int(option_state.get("claims_count", 0) or 0),
        })
    points = _get_points_snapshot(user_id)
    return {
        "user_id": user_id,
        "currency": "MN2",
        "progress": progress,
        "options": options,
        "total_mn2_earned": round(float(user_state.get("total_mn2_earned", 0) or 0), 8),
        "mn2_balance": float(points.get("mn2_balance", 0) or 0),
        "claims": list(user_state.get("claims", []))[-20:],
    }


def _claim_starmap25_crypto(user_id: str, option_id: str):
    state = _load_crypto_state()
    user_state = state.setdefault("users", {}).setdefault(user_id, {
        "total_mn2_earned": 0,
        "claims": [],
        "options": {},
    })
    option = next((o for o in _starmap25_crypto_options() if o["id"] == option_id), None)
    if not option:
        return {"success": False, "error": "Unknown crypto option"}, 404
    progress = _starmap25_crypto_progress(user_id)
    if not _crypto_requirement_met(option, progress):
        return {"success": False, "error": "Crypto option is locked", "progress": progress, "requires": option.get("requires", {})}, 400
    option_state = user_state.setdefault("options", {}).setdefault(option_id, {})
    remaining = _seconds_until(option_state.get("next_claim_at"))
    if remaining > 0:
        return {"success": False, "error": "cooldown", "cooldown_remaining_sec": remaining}, 429
    from datetime import timedelta
    now = _utc_now()
    amount = _crypto_reward_amount(option, progress)
    next_claim_at = (now + timedelta(seconds=int(option.get("cooldown_sec", 0) or 0))).isoformat()
    try:
        from backend.services.unified_points_database import unified_points_db
        unified_points_db.add_points(
            user_id, "mn2_balance", amount,
            source="star_map_25_crypto_claim",
            metadata={"option_id": option_id, "option_name": option.get("name"), "progress": progress},
        )
    except Exception as e:
        return {"success": False, "error": "MN2 award failed: " + str(e)}, 500
    claim = {
        "option_id": option_id,
        "option_name": option.get("name"),
        "amount_mn2": amount,
        "claimed_at": now.isoformat(),
        "next_claim_at": next_claim_at,
        "progress": progress,
    }
    option_state["last_claim_at"] = claim["claimed_at"]
    option_state["next_claim_at"] = next_claim_at
    option_state["claims_count"] = int(option_state.get("claims_count", 0) or 0) + 1
    user_state["total_mn2_earned"] = round(float(user_state.get("total_mn2_earned", 0) or 0) + amount, 8)
    user_state.setdefault("claims", []).append(claim)
    user_state["updated_at"] = now.isoformat()
    _save_crypto_state(state)
    try:
        from backend.routes.social_routes import push_activity
        push_activity(user_id, "starmap25_crypto_claim", f"Claimed {amount:.8f} MN2 from {option.get('name')}", {"option_id": option_id})
    except Exception:
        pass
    return {"success": True, "claim": claim, "crypto": _starmap25_crypto_status(user_id)}, 200


def _starmap25_trophy_definitions():
    return {
        "terra": {"name": "Terra Trophy", "description": "Investigate Terra.", "reward": 25},
        "segmentum_clear": {"name": "Segmentum Clear", "description": "Investigate all five Segmentum fortress points.", "reward": 50},
        "full_clear": {"name": "Full Clear", "description": "Investigate all 25 Star Map systems.", "reward": 100},
        "lore_master": {"name": "Lore Master", "description": "Unlock all 25 lore entries.", "reward": 75},
    }


def _compute_starmap25_trophies(user_id: str):
    data = _load_star_map_25()
    inv = _load_investigations()
    investigated = set(inv.get(user_id, []))
    total_points = len(data.get("points", []))
    segmentums = data.get("segmentums", {})
    fortress_ids = [s.get("fortress_point_id") for s in segmentums.values() if s.get("fortress_point_id")]
    return {
        "terra": "terra_sol" in investigated,
        "segmentum_clear": bool(fortress_ids) and all(fid in investigated for fid in fortress_ids),
        "full_clear": total_points > 0 and len(investigated) >= total_points,
        "lore_master": total_points > 0 and len(investigated) >= total_points,
    }


def _award_starmap25_trophies(user_id: str):
    awards = _load_trophy_awards()
    user_awards = awards.setdefault("users", {}).setdefault(user_id, {"awarded": []})
    already = set(user_awards.get("awarded", []))
    completed = _compute_starmap25_trophies(user_id)
    definitions = _starmap25_trophy_definitions()
    newly_awarded = []
    for trophy_id, is_done in completed.items():
        if not is_done or trophy_id in already:
            continue
        reward = definitions[trophy_id]["reward"]
        try:
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(
                user_id, "trophy_points", reward,
                source="star_map_25_trophy",
                metadata={"trophy_id": trophy_id, "name": definitions[trophy_id]["name"]},
            )
        except Exception:
            pass
        user_awards.setdefault("awarded", []).append(trophy_id)
        newly_awarded.append({"id": trophy_id, **definitions[trophy_id]})
    if newly_awarded:
        from datetime import datetime, timezone
        user_awards["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_trophy_awards(awards)
        _update_starmap25_quests(user_id, trophies=len(newly_awarded))
    return _starmap25_trophy_status(user_id, newly_awarded)


def _starmap25_trophy_status(user_id: str, newly_awarded=None):
    awards = _load_trophy_awards()
    awarded = set(awards.get("users", {}).get(user_id, {}).get("awarded", []))
    completed = _compute_starmap25_trophies(user_id)
    definitions = _starmap25_trophy_definitions()
    trophies = []
    for trophy_id, definition in definitions.items():
        trophies.append({
            "id": trophy_id,
            **definition,
            "completed": bool(completed.get(trophy_id)),
            "awarded": trophy_id in awarded,
        })
    return {"trophies": trophies, "newly_awarded": newly_awarded or []}


def _update_starmap25_quests(user_id: str, investigations: int = 0, game_points: float = 0, trophies: int = 0):
    try:
        from backend.services.user_engagement import update_quest_progress
        if investigations:
            update_quest_progress(user_id, "investigate_starmap", investigations)
            update_quest_progress(user_id, "weekly_starmap", investigations)
        if game_points:
            update_quest_progress(user_id, "earn_game_points", int(max(1, round(game_points))))
        if trophies:
            from backend.services.user_engagement import sync_weekly_trophies_quest
            sync_weekly_trophies_quest(user_id)
    except Exception:
        pass


def _load_events():
    if os.path.exists(STAR_MAP_25_EVENTS_PATH):
        try:
            with open(STAR_MAP_25_EVENTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"events": []}


def _parse_event_time(value):
    if not value:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _active_star_map_events():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    data = _load_events()
    active = []
    upcoming = []
    expired = []
    for event in data.get("events", []):
        start = _parse_event_time(event.get("start_ts"))
        end = _parse_event_time(event.get("end_ts"))
        row = dict(event)
        row["is_active"] = (start is None or start <= now) and (end is None or end > now)
        if row["is_active"]:
            active.append(row)
        elif start and start > now:
            upcoming.append(row)
        else:
            expired.append(row)
    return {
        "active": active,
        "upcoming": upcoming,
        "expired_count": len(expired),
        "updated_at": data.get("updated_at"),
    }


def _event_matches_point(event, point):
    target_point = event.get("target_point_id")
    target_segmentum = event.get("target_segmentum")
    if target_point and target_point != point.get("id"):
        return False
    if target_segmentum and target_segmentum != point.get("segmentum"):
        return False
    return True


def _event_reward_modifier(action, point):
    events = _active_star_map_events().get("active", [])
    matches = []
    multiplier = 1.0
    flat_bonus = 0.0
    for event in events:
        actions = event.get("actions") or []
        if actions and action not in actions:
            continue
        if not _event_matches_point(event, point):
            continue
        multiplier *= float(event.get("reward_multiplier", 1) or 1)
        flat_bonus += float(event.get("flat_bonus", 0) or 0)
        matches.append(event)
    return multiplier, flat_bonus, matches


def _log_event_participation(user_id, action, point_id, event_matches, metadata=None):
    if not event_matches:
        return
    try:
        from datetime import datetime, timezone
        os.makedirs(os.path.dirname(STAR_MAP_25_EVENT_LOG_PATH), exist_ok=True)
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "point_id": point_id,
            "event_ids": [e.get("id") for e in event_matches],
            "metadata": metadata or {},
        }
        with open(STAR_MAP_25_EVENT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def _load_system_levels_config():
    if os.path.exists(STAR_MAP_25_LEVELS_PATH):
        try:
            with open(STAR_MAP_25_LEVELS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"max_level": 5, "level_rules": [], "daily_reset_utc_hour": 0, "daily_reset_bonus_hours": 12}


def _load_walkthrough_config():
    if os.path.exists(STAR_MAP_25_WALKTHROUGH_PATH):
        try:
            with open(STAR_MAP_25_WALKTHROUGH_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"levels": []}


def _load_ai_proof_docs():
    if os.path.exists(STAR_MAP_25_AI_PROOF_DOCS_PATH):
        try:
            with open(STAR_MAP_25_AI_PROOF_DOCS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"proofs": [], "title": "", "description": ""}


def _locked_walkthrough_rows(inv_count: int):
    """Walkthrough tiers not yet reached (upcoming unlocks)."""
    cfg = _load_walkthrough_config()
    rows = []
    for L in sorted(cfg.get("levels", []), key=lambda x: x.get("level", 0)):
        need = int(L.get("min_investigations", 0))
        if inv_count < need:
            rows.append({
                "level": L.get("level"),
                "title": L.get("title", ""),
                "feature": L.get("feature", ""),
                "min_investigations": need,
                "investigations_short": need - inv_count,
            })
    return rows


def _compute_walkthrough_state(inv_count: int):
    """Highest walkthrough tier reached (1–10) and next milestone."""
    cfg = _load_walkthrough_config()
    levels = sorted(cfg.get("levels", []), key=lambda x: x.get("level", 0))
    current = 0
    current_entry = None
    for L in levels:
        if inv_count >= int(L.get("min_investigations", 999)):
            current = int(L.get("level", 0))
            current_entry = L
    next_entry = None
    for L in levels:
        if inv_count < int(L.get("min_investigations", 0)):
            next_entry = L
            break
    return {
        "current_level": max(current, 1) if inv_count > 0 else 0,
        "current_entry": current_entry,
        "next_entry": next_entry,
        "levels": levels,
        "investigated_count": inv_count,
    }


def _sync_starmap25_to_user_profile(user_id: str):
    """Persist investigation multiplier, per-point awards, and walkthrough tier into user profile preferences."""
    try:
        from backend.services.user_onboarding import user_onboarding
        from datetime import datetime, timezone
        profile = user_onboarding.get_user_profile(user_id)
        if not profile:
            return
        prefs_raw = profile.get("preferences")
        if isinstance(prefs_raw, str):
            try:
                prefs = json.loads(prefs_raw) if prefs_raw else {}
            except Exception:
                prefs = {}
        elif isinstance(prefs_raw, dict):
            prefs = dict(prefs_raw)
        else:
            prefs = {}
        inv = _load_investigations()
        investigated = inv.get(user_id, [])
        inv_count = len(investigated)
        sm25 = _load_star_map_25()
        points_list = sm25.get("points", [])
        point_values = {p["id"]: p.get("point_value", 10) for p in points_list}
        total_earned = sum(
            _sm25_investigation_reward(point_values.get(pid, 10)) for pid in investigated
        )
        by_point = {}
        for pid in investigated:
            base = float(point_values.get(pid, 10))
            by_point[pid] = {
                "base": base,
                "multiplier": STAR_MAP_INVESTIGATION_MULTIPLIER,
                "awarded": _sm25_investigation_reward(base),
            }
        wt = _compute_walkthrough_state(inv_count)
        prefs["starmap25"] = {
            "investigation_reward_multiplier": STAR_MAP_INVESTIGATION_MULTIPLIER,
            "investigated_count": inv_count,
            "total_points_earned_map": round(total_earned, 2),
            "reward_by_point": by_point,
            "walkthrough_level": wt["current_level"],
            "walkthrough_next": wt["next_entry"],
            "last_sync_utc": datetime.now(timezone.utc).isoformat(),
        }
        user_onboarding.update_user_profile(user_id, {"preferences": prefs})
    except Exception:
        pass


def _load_buildings():
    if os.path.exists(STAR_MAP_25_BUILDINGS_PATH):
        try:
            with open(STAR_MAP_25_BUILDINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"buildings": []}


def _load_units():
    if os.path.exists(STAR_MAP_25_UNITS_PATH):
        try:
            with open(STAR_MAP_25_UNITS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"units": [], "special_units": []}


def _load_buildup():
    if os.path.exists(STAR_MAP_25_BUILDUP_PATH):
        try:
            with open(STAR_MAP_25_BUILDUP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}


def _save_buildup(data):
    try:
        os.makedirs(os.path.dirname(STAR_MAP_25_BUILDUP_PATH), exist_ok=True)
        with open(STAR_MAP_25_BUILDUP_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _get_user_system_levels(user_id):
    """Compute per-system level (1..5) from investigated + placements. Level 1=investigated, 2=1+building, 3=3+buildings or 2+units, 4=5+placements, 5=8+placements."""
    inv = _load_investigations()
    investigated = set(inv.get(user_id, []))
    buildup = _load_buildup()
    placements = (buildup.get("users", {}).get(user_id, {}).get("placements", []))
    by_point = {}
    for p in placements:
        pid = p.get("point_id", "")
        if pid not in by_point:
            by_point[pid] = {"buildings": 0, "units": 0}
        if p.get("type") == "building":
            by_point[pid]["buildings"] += 1
        else:
            by_point[pid]["units"] += 1
    levels = {}
    sm25 = _load_star_map_25()
    for point in sm25.get("points", []):
        pid = point.get("id", "")
        if pid not in investigated:
            levels[pid] = 0
            continue
        b = by_point.get(pid, {"buildings": 0, "units": 0})
        total = b["buildings"] + b["units"]
        if total >= 8:
            levels[pid] = 5
        elif total >= 5:
            levels[pid] = 4
        elif b["buildings"] >= 3 or b["units"] >= 2:
            levels[pid] = 3
        elif b["buildings"] >= 1:
            levels[pid] = 2
        else:
            levels[pid] = 1
    return levels


def _next_daily_reset_utc():
    """Return next daily reset datetime (midnight UTC) and whether we're inside the bonus window (12h after reset)."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now >= today_midnight + timedelta(hours=12):
        next_reset = today_midnight + timedelta(days=1)
    else:
        next_reset = today_midnight
    in_bonus_window = now < today_midnight + timedelta(hours=12)
    return next_reset.isoformat(), in_bonus_window


# Point id -> tags for buildup bonus (fortress, forge, legion_homeworld, naval, throne)
def _point_tags(point_id):
    try:
        data = _load_star_map_25()
        point = next((p for p in data.get("points", []) if p.get("id") == point_id), None)
        if point and point.get("tags"):
            return point.get("tags", [])
    except Exception:
        pass
    tags_map = {
        "terra_sol": ["throne", "life_bearing"],
        "mars_sol": ["forge", "fortress"],
        "cypra_mundi": ["fortress"],
        "hydraphur": ["fortress", "naval"],
        "bakka": ["fortress"],
        "kar_duniash": ["fortress"],
        "macragge": ["legion_homeworld"],
        "fenris": ["legion_homeworld"],
        "cadia": ["fortress"],
        "baal": ["legion_homeworld"],
        "nocturne": ["legion_homeworld"],
        "medusa": ["legion_homeworld"],
        "olympia": ["traitor"],
        "caliban": ["legion_homeworld"],
        "chogoris": ["legion_homeworld"],
        "barbarus": ["traitor"],
        "chemos": ["traitor"],
        "colchis": ["traitor"],
        "nostramo": ["traitor"],
        "prospero": ["legion_homeworld"],
        "cthonia": ["traitor"],
        "deliverance": ["legion_homeworld"],
        "nuceria": ["traitor"],
        "inwit": ["legion_homeworld"],
        "ryza": ["forge"],
    }
    return tags_map.get(point_id, [])


def _compute_pending_buildup_points(user_id):
    """Compute game_points generated by user's buildings and units since last collect (or since placed). Applies daily_reset_bonus (2x) for 12h after midnight UTC."""
    from datetime import datetime, timezone
    _, in_bonus_window = _next_daily_reset_utc()
    buildup = _load_buildup()
    users = buildup.get("users", {})
    user_data = users.get(user_id, {})
    placements = user_data.get("placements", [])
    last_collect = user_data.get("last_collect_ts")
    buildings_data = _load_buildings()
    units_data = _load_units()
    buildings_by_id = {b["id"]: b for b in buildings_data.get("buildings", [])}
    units_by_id = {u["id"]: u for u in units_data.get("units", [])}
    for u in units_data.get("special_units", []):
        units_by_id[u["id"]] = u
    now = datetime.now(timezone.utc)
    total = 0.0
    for p in placements:
        placed_at = p.get("at", now.isoformat())
        try:
            start = datetime.fromisoformat(placed_at.replace("Z", "+00:00"))
        except Exception:
            start = now
        if last_collect:
            try:
                start = max(start, datetime.fromisoformat(last_collect.replace("Z", "+00:00")))
            except Exception:
                pass
        days = max(0, (now - start).total_seconds() / 86400.0)
        pts_per_day = 0.0
        if p.get("type") == "building":
            b = buildings_by_id.get(p.get("id", ""))
            if b:
                pts_per_day = float(b.get("points_per_day", 0))
                bonus_tags = b.get("bonus_on_tags", [])
                pt_tags = _point_tags(p.get("point_id", ""))
                if bonus_tags and any(t in pt_tags for t in bonus_tags):
                    pts_per_day = float(b.get("points_per_day", pts_per_day))
                if b.get("daily_reset_bonus") and in_bonus_window:
                    pts_per_day *= float(_load_system_levels_config().get("daily_reset_bonus_multiplier", 2.0))
        elif p.get("type") == "unit":
            u = units_by_id.get(p.get("id", ""))
            if u:
                pts_per_day = float(u.get("points_per_day", 0))
                bonus_tags = u.get("bonus_tags", [])
                pt_tags = _point_tags(p.get("point_id", ""))
                if bonus_tags and any(t in pt_tags for t in bonus_tags):
                    pts_per_day += float(u.get("bonus_points_per_day", 0))
        total += days * pts_per_day
    return round(total, 2)


@star_map_bp.route("/api/star-map", methods=["GET"])
@star_map_bp.route("/api/game/hunters/star-map", methods=["GET"])
def get_star_map():
    """Get star map: 7 nearest stars, planets, life-bearing b; info and flyers slots."""
    try:
        data = _load_star_map()
        return jsonify({"success": True, "star_map": data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/stars", methods=["GET"])
def get_stars_list():
    """List stars only (for UI dropdowns, etc.)."""
    try:
        data = _load_star_map()
        stars = data.get("stars", [])
        return jsonify({"success": True, "stars": stars}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------- Star Map 25 (Imperium Investigation Grid) ----------

@star_map_bp.route("/api/star-map/25", methods=["GET"])
def get_star_map_25():
    """Get full 25-point starmap (WH40K Segmentum + Legion homeworlds)."""
    try:
        data = _load_star_map_25()
        return jsonify({"success": True, "star_map_25": data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _star_map_25_point_state(user_id, point):
    point_id = point.get("id", "")
    investigated = set(_load_investigations().get(user_id, []))
    invasion_user = _load_invasions().get("users", {}).get(user_id, {})
    invaded = set(invasion_user.get("invaded_ids", []))
    levels = _get_user_system_levels(user_id)
    buildup_user = _load_buildup().get("users", {}).get(user_id, {})
    placements = [
        p for p in buildup_user.get("placements", [])
        if p.get("point_id") == point_id
    ]
    return {
        "investigated": point_id in investigated,
        "secured": point_id in invaded,
        "level": levels.get(point_id, 0),
        "placements": placements,
        "invasion_blurb": (invasion_user.get("blurbs") or {}).get(point_id, ""),
        "invasion_unit": (invasion_user.get("units") or {}).get(point_id, ""),
        "invasion_reward": (invasion_user.get("rewards") or {}).get(point_id, 0),
    }


def _star_map_25_segmentum_summary(user_id, segmentum_name):
    data = _load_star_map_25()
    points = [
        p for p in data.get("points", [])
        if str(p.get("segmentum", "")).lower() == str(segmentum_name).lower()
    ]
    if not points:
        return None
    states = [_star_map_25_point_state(user_id, p) for p in points]
    metadata = (data.get("segmentums") or {}).get(points[0].get("segmentum"), {})
    return {
        "segmentum": points[0].get("segmentum", segmentum_name),
        "metadata": metadata,
        "point_count": len(points),
        "investigated_count": sum(1 for s in states if s.get("investigated")),
        "secured_count": sum(1 for s in states if s.get("secured")),
        "max_level_count": sum(1 for s in states if int(s.get("level") or 0) >= 5),
        "total_point_value": sum(float(p.get("point_value", 0) or 0) for p in points),
        "points": [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "index": p.get("index"),
                "point_value": p.get("point_value", 0),
                "tags": p.get("tags", []),
                "state": state,
            }
            for p, state in zip(points, states)
        ],
    }


@star_map_bp.route("/api/star-map/25/point/<point_id>", methods=["GET"])
def get_star_map_25_point(point_id):
    """Get one Star Map 25 point with user-specific investigation, buildup, and invasion state."""
    user_id = request.args.get("user_id") or "default_user"
    try:
        data = _load_star_map_25()
        point = next((p for p in data.get("points", []) if p.get("id") == point_id), None)
        if not point:
            return jsonify({"success": False, "error": "Unknown point_id"}), 404
        return jsonify({
            "success": True,
            "user_id": user_id,
            "point": point,
            "state": _star_map_25_point_state(user_id, point),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/segmentums", methods=["GET"])
def list_star_map_25_segmentums():
    """List Segmentum summaries with per-user progress."""
    user_id = request.args.get("user_id") or "default_user"
    try:
        data = _load_star_map_25()
        names = sorted({p.get("segmentum", "Unknown") for p in data.get("points", [])})
        summaries = [_star_map_25_segmentum_summary(user_id, name) for name in names]
        return jsonify({
            "success": True,
            "user_id": user_id,
            "segmentums": [s for s in summaries if s],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/segmentum/<segmentum>", methods=["GET"])
def get_star_map_25_segmentum(segmentum):
    """Get one Segmentum with per-point and aggregate user progress."""
    user_id = request.args.get("user_id") or "default_user"
    try:
        summary = _star_map_25_segmentum_summary(user_id, segmentum)
        if not summary:
            return jsonify({"success": False, "error": "Unknown segmentum"}), 404
        return jsonify({"success": True, "user_id": user_id, "segmentum": summary}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _star_map_25_health_payload():
    checks = []

    def add_check(name, ok, detail=None):
        checks.append({"name": name, "ok": bool(ok), "detail": detail or ""})

    data = _load_star_map_25()
    points = data.get("points", [])
    add_check("star_map_25_json", bool(points), f"{len(points)} points")
    add_check("point_count", len(points) == 25, f"expected 25, got {len(points)}")
    ids = [p.get("id") for p in points]
    add_check("unique_point_ids", len(ids) == len(set(ids)), f"{len(set(ids))} unique")
    add_check("segmentum_metadata", bool(data.get("segmentums")), f"{len(data.get('segmentums') or {})} segmentums")

    for label, path in [
        ("investigations_state", STAR_MAP_25_INVESTIGATIONS_PATH),
        ("buildup_state", STAR_MAP_25_BUILDUP_PATH),
        ("invasions_state", STAR_MAP_25_INVASIONS_PATH),
        ("events_state", STAR_MAP_25_EVENTS_PATH),
        ("trophies_state", STAR_MAP_25_TROPHIES_PATH),
        ("crypto_state", STAR_MAP_25_CRYPTO_PATH),
    ]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
                add_check(label, True, "readable JSON")
            except Exception as exc:
                add_check(label, False, str(exc))
        else:
            add_check(label, True, "not created yet")

    try:
        state_dir = os.path.dirname(STAR_MAP_25_INVESTIGATIONS_PATH)
        os.makedirs(state_dir, exist_ok=True)
        probe = os.path.join(state_dir, ".starmap25_health_probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        add_check("state_directory_writable", True, state_dir)
    except Exception as exc:
        add_check("state_directory_writable", False, str(exc))

    return {
        "success": all(c["ok"] for c in checks),
        "checked_at": _utc_now().isoformat(),
        "checks": checks,
    }


@star_map_bp.route("/api/star-map/25/health", methods=["GET"])
def star_map_25_health():
    """Health check for Star Map 25 data and writable state files."""
    try:
        payload = _star_map_25_health_payload()
        return jsonify(payload), 200 if payload.get("success") else 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _fallback_planet_intel(point, planet_name):
    """Five-level drill-down when planet_intel is absent from JSON."""
    seg = point.get("segmentum") or "Unknown"
    lb = (point.get("life_bearing") or "").strip()
    life_label = point.get("life_label") or ""
    info = (point.get("info") or "")[:280]
    lore = (point.get("lore") or "")[:320]
    if planet_name.strip() == lb:
        alien = (
            f"Primary biosphere match ({life_label}). "
            f"Alien races (Imperial taxonomy): native population on record. Already had this behavior."
        )
    else:
        alien = (
            f"Secondary body {planet_name} in system. "
            f"No primary xenos match; cross-ref life-bearing {lb or 'n/a'}. Already had this behavior."
        )
    return {
        "depth_levels": [
            {"depth": 1, "title": "Orbital shell", "body": f"Segmentum {seg}. Host: {point.get('host_star', '—')}."},
            {"depth": 2, "title": "Climate & crust", "body": info or "No extended survey."},
            {"depth": 3, "title": "Alien races", "body": alien},
            {"depth": 4, "title": "Threat & compliance", "body": "Compliance scan: strategic asset under Segmentum doctrine."},
            {"depth": 5, "title": "Strategic closure", "body": lore or "Archive pending."},
        ]
    }


@star_map_bp.route("/api/star-map/25/planet-intel", methods=["GET"])
def get_star_map_25_planet_intel():
    """Deep five-level stats for a planet in a system (from JSON or generated fallback)."""
    point_id = (request.args.get("point_id") or "").strip()
    planet = (request.args.get("planet") or "").strip()
    if not point_id or not planet:
        return jsonify({"success": False, "error": "point_id and planet required"}), 400
    try:
        sm25 = _load_star_map_25()
        point = next((p for p in sm25.get("points", []) if p.get("id") == point_id), None)
        if not point:
            return jsonify({"success": False, "error": "Unknown point_id"}), 404
        planets = point.get("planets") or []
        if planet not in planets:
            return jsonify({"success": False, "error": "Planet not in this system"}), 400
        raw = (point.get("planet_intel") or {}).get(planet)
        if raw and isinstance(raw, dict) and raw.get("depth_levels"):
            intel = raw
        elif raw and isinstance(raw, dict) and isinstance(raw.get("levels"), list):
            intel = {"depth_levels": raw["levels"]}
        else:
            intel = _fallback_planet_intel(point, planet)
        return jsonify({
            "success": True,
            "point_id": point_id,
            "planet": planet,
            "system_name": point.get("name", ""),
            "intel": intel,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/status", methods=["GET"])
def get_star_map_25_status():
    """Get user's investigation status: investigated point IDs and total points earned."""
    user_id = request.args.get("user_id") or "default_user"
    try:
        inv = _load_investigations()
        investigated = inv.get(user_id, [])
        data = _load_star_map_25()
        points_list = data.get("points", [])
        point_values = {p["id"]: p.get("point_value", 10) for p in points_list}
        booster_multiplier = _starmap25_booster_multiplier(user_id)
        total_earned = sum(
            _sm25_investigation_reward(point_values.get(pid, 10)) for pid in investigated
        )
        invasions = _load_invasions()
        invasion_user = invasions.get("users", {}).get(user_id, {})
        invaded_ids = invasion_user.get("invaded_ids", [])
        invasion_rewards = invasion_user.get("rewards", {})
        total_invasion_points = sum(float(v or 0) for v in invasion_rewards.values())
        inv_len = len(investigated)
        wt = _compute_walkthrough_state(inv_len)
        trophy_status = _award_starmap25_trophies(user_id)
        points_snapshot = _get_points_snapshot(user_id)
        return jsonify({
            "success": True,
            "user_id": user_id,
            "investigated_ids": investigated,
            "invaded_ids": invaded_ids,
            "invasion_blurbs": invasion_user.get("blurbs", {}),
            "invasion_units": invasion_user.get("units", {}),
            "investigated_count": inv_len,
            "invaded_count": len(invaded_ids),
            "total_points": len(points_list),
            "total_points_earned": total_earned,
            "total_invasion_points_earned": total_invasion_points,
            "investigation_reward_multiplier": STAR_MAP_INVESTIGATION_MULTIPLIER,
            "starmap25_booster_multiplier": booster_multiplier,
            "active_starmap25_boosters": _active_starmap25_boosters(user_id),
            "game_points_balance": float(points_snapshot.get("game_points", 0) or 0),
            "mn2_balance": float(points_snapshot.get("mn2_balance", 0) or 0),
            "crypto": _starmap25_crypto_status(user_id),
            "trophies": trophy_status.get("trophies", []),
            "newly_awarded_trophies": trophy_status.get("newly_awarded", []),
            "walkthrough": {
                "current_level": wt["current_level"],
                "current_feature": (wt.get("current_entry") or {}).get("feature"),
                "current_title": (wt.get("current_entry") or {}).get("title"),
                "next": wt.get("next_entry"),
                "levels": wt.get("levels", []),
            },
            "reward_formula": "base_point_value × investigation_reward_multiplier × active_starmap25_booster_multiplier = awarded",
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/sync-profile", methods=["POST"])
def sync_star_map_25_profile():
    """Persist multiplier, per-point awards, and walkthrough tier to user profile (call on monitor load or after play)."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id") or request.args.get("user_id") or "default_user"
        _sync_starmap25_to_user_profile(user_id)
        return jsonify({"success": True, "user_id": user_id}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/investigate", methods=["POST"])
def investigate_star_map_25_point():
    """Investigate a point; award game_points once per point per user."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id") or request.args.get("user_id") or "default_user"
        point_id = (data.get("point_id") or data.get("pointId") or "").strip()
        if not point_id:
            return jsonify({"success": False, "error": "point_id required"}), 400

        sm25 = _load_star_map_25()
        points_list = sm25.get("points", [])
        point = next((p for p in points_list if p.get("id") == point_id), None)
        if not point:
            return jsonify({"success": False, "error": "Unknown point_id"}), 404

        inv = _load_investigations()
        if user_id not in inv:
            inv[user_id] = []
        if point_id in inv[user_id]:
            return jsonify({
                "success": True,
                "already_investigated": True,
                "user_id": user_id,
                "point_id": point_id,
                "points_awarded": 0,
                "message": "Already investigated",
            }), 200

        base_amount = _sm25_investigation_reward(point.get("point_value", 10))
        booster_multiplier = _starmap25_booster_multiplier(user_id)
        amount = round(base_amount * booster_multiplier, 2)
        try:
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(
                user_id, "game_points", amount,
                source="star_map_25_investigate",
                metadata={
                    "point_id": point_id,
                    "point_name": point.get("name", ""),
                    "base_amount": base_amount,
                    "booster_multiplier": booster_multiplier,
                    "active_booster_ids": [b.get("id") for b in _active_starmap25_boosters(user_id)],
                },
            )
        except Exception as e:
            return jsonify({"success": False, "error": "Points award failed: " + str(e)}), 500

        inv[user_id] = inv[user_id] + [point_id]
        _save_investigations(inv)
        _sync_starmap25_to_user_profile(user_id)
        _update_starmap25_quests(user_id, investigations=1, game_points=amount)
        trophy_status = _award_starmap25_trophies(user_id)
        try:
            from backend.routes.social_routes import push_activity
            push_activity(user_id, "starmap25_investigate", f"Investigated {point.get('name', point_id)}", {"point_id": point_id})
        except Exception:
            pass
        return jsonify({
            "success": True,
            "already_investigated": False,
            "user_id": user_id,
            "point_id": point_id,
            "point_name": point.get("name", ""),
            "points_awarded": amount,
            "base_points_awarded": base_amount,
            "booster_multiplier": booster_multiplier,
            "active_starmap25_boosters": _active_starmap25_boosters(user_id),
            "newly_awarded_trophies": trophy_status.get("newly_awarded", []),
            "lore": point.get("lore", ""),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------- Star Map 25 Buildup (units + buildings → generate points) ----------

@star_map_bp.route("/api/star-map/25/buildings", methods=["GET"])
def get_star_map_25_buildings():
    """List building types: id, name, icon, points_per_day, build_cost."""
    try:
        data = _load_buildings()
        return jsonify({"success": True, "buildings": data.get("buildings", [])}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/units", methods=["GET"])
def get_star_map_25_units():
    """List units and special_units: id, name, icon, points_per_day, deploy_cost."""
    try:
        data = _load_units()
        return jsonify({
            "success": True,
            "units": data.get("units", []),
            "special_units": data.get("special_units", []),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/events", methods=["GET"])
def get_star_map_25_events():
    """Return active/upcoming temporary Star Map 25 events with timing and reward modifiers."""
    try:
        state = _active_star_map_events()
        return jsonify({
            "success": True,
            "active_events": state["active"],
            "upcoming_events": state["upcoming"],
            "expired_count": state["expired_count"],
            "updated_at": state.get("updated_at"),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/crypto", methods=["GET"])
def get_star_map_25_crypto():
    """Per-user in-game Star Map crypto status. Awards use internal mn2_balance, not wallet transfers."""
    user_id = request.args.get("user_id") or "default_user"
    try:
        return jsonify({"success": True, **_starmap25_crypto_status(user_id)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/crypto/claim", methods=["POST"])
def claim_star_map_25_crypto():
    """Claim an in-game MN2 earning option when unlocked and off cooldown."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id") or request.args.get("user_id") or "default_user"
        option_id = (data.get("option_id") or "").strip()
        if not option_id:
            return jsonify({"success": False, "error": "option_id required"}), 400
        body, status = _claim_starmap25_crypto(user_id, option_id)
        return jsonify(body), status
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/buildup", methods=["GET"])
def get_star_map_25_buildup():
    """Get user's buildup state: placements (buildings + units on planets) and pending_points (since last collect)."""
    user_id = request.args.get("user_id") or "default_user"
    try:
        buildup = _load_buildup()
        user_data = buildup.get("users", {}).get(user_id, {})
        placements = user_data.get("placements", [])
        pending_points = _compute_pending_buildup_points(user_id)
        return jsonify({
            "success": True,
            "user_id": user_id,
            "placements": placements,
            "last_collect_ts": user_data.get("last_collect_ts"),
            "pending_points": pending_points,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/build", methods=["POST"])
def build_star_map_25():
    """Place a building on a planet. Requires investigated point; deducts build_cost from game_points."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id") or request.args.get("user_id") or "default_user"
        point_id = (data.get("point_id") or "").strip()
        planet = (data.get("planet") or "").strip()
        building_id = (data.get("building_id") or "").strip()
        if not point_id or not planet or not building_id:
            return jsonify({"success": False, "error": "point_id, planet, building_id required"}), 400

        sm25 = _load_star_map_25()
        point = next((p for p in sm25.get("points", []) if p.get("id") == point_id), None)
        if not point:
            return jsonify({"success": False, "error": "Unknown point_id"}), 404
        if planet not in (point.get("planets") or []):
            return jsonify({"success": False, "error": "Planet not in this system"}), 400

        inv = _load_investigations()
        if point_id not in inv.get(user_id, []):
            return jsonify({"success": False, "error": "Investigate this system first"}), 400

        buildings_data = _load_buildings()
        building = next((b for b in buildings_data.get("buildings", []) if b.get("id") == building_id), None)
        if not building:
            return jsonify({"success": False, "error": "Unknown building_id"}), 404
        required_level = int(building.get("min_level", 1))
        user_levels = _get_user_system_levels(user_id)
        if user_levels.get(point_id, 0) < required_level:
            return jsonify({"success": False, "error": "System level too low (need level %d)" % required_level}), 400
        build_cost = int(building.get("build_cost", 0))
        if build_cost > 0:
            try:
                from backend.services.unified_points_database import unified_points_db
                all_pts = unified_points_db.get_all_points(user_id) or {}
                balance = float((all_pts.get("points") or {}).get("game_points", 0) or 0)
                if balance < build_cost:
                    return jsonify({"success": False, "error": "Not enough game_points to build"}), 400
                unified_points_db.add_points(
                    user_id, "game_points", -build_cost,
                    source="star_map_25_build",
                    metadata={"point_id": point_id, "planet": planet, "building_id": building_id},
                )
            except Exception as e:
                return jsonify({"success": False, "error": "Points deduction failed: " + str(e)}), 500

        from datetime import datetime, timezone
        buildup = _load_buildup()
        if user_id not in buildup.setdefault("users", {}):
            buildup["users"][user_id] = {"placements": [], "last_collect_ts": None}
        placements = buildup["users"][user_id]["placements"]
        slot_key = f"{point_id}|{planet}"
        existing = [pl for pl in placements if pl.get("type") == "building" and pl.get("point_id") == point_id and pl.get("planet") == planet]
        if existing:
            return jsonify({"success": False, "error": "Already have a building on this planet"}), 400
        placements.append({
            "point_id": point_id,
            "planet": planet,
            "type": "building",
            "id": building_id,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        _save_buildup(buildup)
        event_multiplier, event_flat_bonus, event_matches = _event_reward_modifier("build", point)
        booster_multiplier = _starmap25_booster_multiplier(user_id)
        base_event_bonus = round((float(building.get("points_per_day", 0) or 0) * max(event_multiplier - 1.0, 0)) + event_flat_bonus, 2)
        event_bonus = round(base_event_bonus * booster_multiplier, 2)
        if event_bonus > 0:
            try:
                from backend.services.unified_points_database import unified_points_db
                unified_points_db.add_points(
                    user_id, "game_points", event_bonus,
                    source="star_map_25_event_build",
                    metadata={
                        "point_id": point_id,
                        "planet": planet,
                        "building_id": building_id,
                        "event_ids": [e.get("id") for e in event_matches],
                        "base_event_bonus_points": base_event_bonus,
                        "booster_multiplier": booster_multiplier,
                    },
                )
            except Exception:
                event_bonus = 0
        _update_starmap25_quests(user_id, game_points=event_bonus)
        _log_event_participation(user_id, "build", point_id, event_matches, {
            "planet": planet,
            "building_id": building_id,
            "event_bonus_points": event_bonus,
            "booster_multiplier": booster_multiplier,
        })
        return jsonify({
            "success": True,
            "user_id": user_id,
            "point_id": point_id,
            "planet": planet,
            "building_id": building_id,
            "points_per_day": building.get("points_per_day", 0),
            "event_bonus_points": event_bonus,
            "base_event_bonus_points": base_event_bonus,
            "booster_multiplier": booster_multiplier,
            "event_ids": [e.get("id") for e in event_matches],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/deploy", methods=["POST"])
def deploy_star_map_25():
    """Deploy a unit (or special unit) to a planet. Requires investigated point; deducts deploy_cost if any."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id") or request.args.get("user_id") or "default_user"
        point_id = (data.get("point_id") or "").strip()
        planet = (data.get("planet") or "").strip()
        unit_id = (data.get("unit_id") or "").strip()
        if not point_id or not planet or not unit_id:
            return jsonify({"success": False, "error": "point_id, planet, unit_id required"}), 400

        sm25 = _load_star_map_25()
        point = next((p for p in sm25.get("points", []) if p.get("id") == point_id), None)
        if not point:
            return jsonify({"success": False, "error": "Unknown point_id"}), 404
        if planet not in (point.get("planets") or []):
            return jsonify({"success": False, "error": "Planet not in this system"}), 400

        inv = _load_investigations()
        if point_id not in inv.get(user_id, []):
            return jsonify({"success": False, "error": "Investigate this system first"}), 400

        units_data = _load_units()
        unit = next((u for u in units_data.get("units", []) + units_data.get("special_units", []) if u.get("id") == unit_id), None)
        if not unit:
            return jsonify({"success": False, "error": "Unknown unit_id"}), 404
        deploy_cost = int(unit.get("deploy_cost", 0))
        if deploy_cost > 0:
            try:
                from backend.services.unified_points_database import unified_points_db
                all_pts = unified_points_db.get_all_points(user_id) or {}
                balance = float((all_pts.get("points") or {}).get("game_points", 0) or 0)
                if balance < deploy_cost:
                    return jsonify({"success": False, "error": "Not enough game_points to deploy"}), 400
                unified_points_db.add_points(
                    user_id, "game_points", -deploy_cost,
                    source="star_map_25_deploy",
                    metadata={"point_id": point_id, "planet": planet, "unit_id": unit_id},
                )
            except Exception as e:
                return jsonify({"success": False, "error": "Points deduction failed: " + str(e)}), 500

        from datetime import datetime, timezone
        buildup = _load_buildup()
        if user_id not in buildup.setdefault("users", {}):
            buildup["users"][user_id] = {"placements": [], "last_collect_ts": None}
        placements = buildup["users"][user_id]["placements"]
        placements.append({
            "point_id": point_id,
            "planet": planet,
            "type": "unit",
            "id": unit_id,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        _save_buildup(buildup)
        event_multiplier, event_flat_bonus, event_matches = _event_reward_modifier("deploy", point)
        booster_multiplier = _starmap25_booster_multiplier(user_id)
        base_event_bonus = round((float(unit.get("points_per_day", 0) or 0) * max(event_multiplier - 1.0, 0)) + event_flat_bonus, 2)
        event_bonus = round(base_event_bonus * booster_multiplier, 2)
        if event_bonus > 0:
            try:
                from backend.services.unified_points_database import unified_points_db
                unified_points_db.add_points(
                    user_id, "game_points", event_bonus,
                    source="star_map_25_event_deploy",
                    metadata={
                        "point_id": point_id,
                        "planet": planet,
                        "unit_id": unit_id,
                        "event_ids": [e.get("id") for e in event_matches],
                        "base_event_bonus_points": base_event_bonus,
                        "booster_multiplier": booster_multiplier,
                    },
                )
            except Exception:
                event_bonus = 0
        _update_starmap25_quests(user_id, game_points=event_bonus)
        _log_event_participation(user_id, "deploy", point_id, event_matches, {
            "planet": planet,
            "unit_id": unit_id,
            "event_bonus_points": event_bonus,
            "booster_multiplier": booster_multiplier,
        })
        return jsonify({
            "success": True,
            "user_id": user_id,
            "point_id": point_id,
            "planet": planet,
            "unit_id": unit_id,
            "points_per_day": unit.get("points_per_day", 0),
            "event_bonus_points": event_bonus,
            "base_event_bonus_points": base_event_bonus,
            "booster_multiplier": booster_multiplier,
            "event_ids": [e.get("id") for e in event_matches],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/collect", methods=["POST"])
def collect_star_map_25_buildup():
    """Collect pending game_points from all buildings and deployed units; update last_collect_ts."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id") or request.args.get("user_id") or "default_user"
        pending = _compute_pending_buildup_points(user_id)
        if pending <= 0:
            buildup = _load_buildup()
            user_data = buildup.get("users", {}).get(user_id, {})
            from datetime import datetime, timezone
            if user_id in buildup.get("users", {}):
                buildup["users"][user_id]["last_collect_ts"] = datetime.now(timezone.utc).isoformat()
                _save_buildup(buildup)
            return jsonify({
                "success": True,
                "user_id": user_id,
                "points_collected": 0,
                "message": "Nothing to collect",
            }), 200
        try:
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(
                user_id, "game_points", pending,
                source="star_map_25_buildup_collect",
                metadata={"pending": pending},
            )
        except Exception as e:
            return jsonify({"success": False, "error": "Points award failed: " + str(e)}), 500
        from datetime import datetime, timezone
        buildup = _load_buildup()
        if user_id not in buildup.setdefault("users", {}):
            buildup["users"][user_id] = {"placements": [], "last_collect_ts": None}
        buildup["users"][user_id]["last_collect_ts"] = datetime.now(timezone.utc).isoformat()
        _save_buildup(buildup)
        _update_starmap25_quests(user_id, game_points=pending)
        try:
            from backend.routes.social_routes import push_activity
            push_activity(user_id, "starmap25_collect", f"Collected {pending} game_points from buildup", {"points": pending})
        except Exception:
            pass
        try:
            sm25 = _load_star_map_25()
            by_point = {p.get("id"): p for p in sm25.get("points", [])}
            event_matches = []
            placements = buildup.get("users", {}).get(user_id, {}).get("placements", [])
            seen = set()
            for placement in placements:
                point = by_point.get(placement.get("point_id"))
                if not point:
                    continue
                _, _, matches = _event_reward_modifier("collect", point)
                for event in matches:
                    eid = event.get("id")
                    if eid not in seen:
                        seen.add(eid)
                        event_matches.append(event)
            _log_event_participation(user_id, "collect", "multiple", event_matches, {"points_collected": pending})
        except Exception:
            pass
        return jsonify({
            "success": True,
            "user_id": user_id,
            "points_collected": pending,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/invade", methods=["POST"])
def invade_star_map_25():
    """Secure an investigated system with an already deployed unit; awards a one-time invasion bonus."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id") or request.args.get("user_id") or "default_user"
        point_id = (data.get("point_id") or "").strip()
        unit_id = (data.get("unit_id") or "").strip()
        if not point_id or not unit_id:
            return jsonify({"success": False, "error": "point_id and unit_id required"}), 400

        sm25 = _load_star_map_25()
        point = next((p for p in sm25.get("points", []) if p.get("id") == point_id), None)
        if not point:
            return jsonify({"success": False, "error": "Unknown point_id"}), 404

        inv = _load_investigations()
        if point_id not in inv.get(user_id, []):
            return jsonify({"success": False, "error": "Investigate this system first"}), 400

        units_data = _load_units()
        all_units = units_data.get("units", []) + units_data.get("special_units", [])
        unit = next((u for u in all_units if u.get("id") == unit_id), None)
        if not unit:
            return jsonify({"success": False, "error": "Unknown unit_id"}), 404

        buildup = _load_buildup()
        placements = buildup.get("users", {}).get(user_id, {}).get("placements", [])
        deployed = next((
            p for p in placements
            if p.get("type") == "unit" and p.get("point_id") == point_id and p.get("id") == unit_id
        ), None)
        if not deployed:
            return jsonify({"success": False, "error": "Deploy this unit to the system before invading"}), 400

        invasions = _load_invasions()
        users = invasions.setdefault("users", {})
        user_state = users.setdefault(user_id, {"invaded_ids": [], "blurbs": {}, "units": {}, "rewards": {}})
        if point_id in user_state.get("invaded_ids", []):
            return jsonify({
                "success": True,
                "already_invaded": True,
                "user_id": user_id,
                "point_id": point_id,
                "unit_id": user_state.get("units", {}).get(point_id, unit_id),
                "points_awarded": 0,
                "blurb": user_state.get("blurbs", {}).get(point_id, ""),
                "message": "Already secured",
            }), 200

        base_reward = 10 + int(unit.get("points_per_day", 0) or 0) * 2 + int(unit.get("bonus_points_per_day", 0) or 0)
        event_multiplier, event_flat_bonus, event_matches = _event_reward_modifier("invade", point)
        reward = round((base_reward * event_multiplier) + event_flat_bonus, 2)
        unit_name = unit.get("name", unit_id)
        point_name = point.get("name", point_id)
        event_suffix = ""
        if event_matches:
            event_suffix = " Event bonus: " + ", ".join(e.get("name", e.get("id", "event")) for e in event_matches) + "."
        blurb = f"{unit_name} secured {point_name}; the system is now marked as held.{event_suffix}"
        try:
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(
                user_id, "game_points", reward,
                source="star_map_25_invade",
                metadata={
                    "point_id": point_id,
                    "point_name": point_name,
                    "unit_id": unit_id,
                    "base_reward": base_reward,
                    "event_multiplier": event_multiplier,
                    "event_flat_bonus": event_flat_bonus,
                    "event_ids": [e.get("id") for e in event_matches],
                },
            )
        except Exception as e:
            return jsonify({"success": False, "error": "Points award failed: " + str(e)}), 500

        from datetime import datetime, timezone
        user_state.setdefault("invaded_ids", []).append(point_id)
        user_state.setdefault("blurbs", {})[point_id] = blurb
        user_state.setdefault("units", {})[point_id] = unit_id
        user_state.setdefault("rewards", {})[point_id] = reward
        user_state["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_invasions(invasions)
        _log_event_participation(user_id, "invade", point_id, event_matches, {
            "unit_id": unit_id,
            "base_reward": base_reward,
            "points_awarded": reward,
            "event_multiplier": event_multiplier,
            "event_flat_bonus": event_flat_bonus,
        })
        try:
            from backend.routes.social_routes import push_activity
            push_activity(user_id, "starmap25_invade", f"Secured {point_name}", {"point_id": point_id, "unit_id": unit_id})
        except Exception:
            pass
        return jsonify({
            "success": True,
            "already_invaded": False,
            "user_id": user_id,
            "point_id": point_id,
            "point_name": point_name,
            "unit_id": unit_id,
            "points_awarded": reward,
            "base_points_awarded": base_reward,
            "event_multiplier": event_multiplier,
            "event_flat_bonus": event_flat_bonus,
            "event_ids": [e.get("id") for e in event_matches],
            "blurb": blurb,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/levels", methods=["GET"])
def get_star_map_25_levels():
    """Get user's system levels (1–5 per point), level rules, next daily reset, and whether in bonus window."""
    user_id = request.args.get("user_id") or "default_user"
    try:
        levels = _get_user_system_levels(user_id)
        next_reset_iso, in_bonus_window = _next_daily_reset_utc()
        config = _load_system_levels_config()
        sm25 = _load_star_map_25()
        points_with_levels = []
        for p in sm25.get("points", []):
            pid = p.get("id", "")
            points_with_levels.append({
                "point_id": pid,
                "name": p.get("name", ""),
                "level": levels.get(pid, 0),
                "segmentum": p.get("segmentum", ""),
            })
        return jsonify({
            "success": True,
            "user_id": user_id,
            "system_levels": levels,
            "points_with_levels": points_with_levels,
            "level_rules": config.get("level_rules", []),
            "max_level": config.get("max_level", 5),
            "next_daily_reset_utc": next_reset_iso,
            "in_daily_reset_bonus_window": in_bonus_window,
            "daily_reset_bonus_hours": config.get("daily_reset_bonus_hours", 12),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _read_starmap25_event_rows(limit=500):
    rows = []
    if not os.path.exists(STAR_MAP_25_EVENT_LOG_PATH):
        return rows
    try:
        with open(STAR_MAP_25_EVENT_LOG_PATH, "r", encoding="utf-8") as f:
            raw_rows = f.readlines()[-limit:]
        for raw in raw_rows:
            try:
                rows.append(json.loads(raw))
            except Exception:
                continue
    except Exception:
        return []
    return rows


def _star_map_25_analytics_payload(user_id=None):
    rows = _read_starmap25_event_rows()
    if user_id:
        rows = [r for r in rows if r.get("user_id") == user_id]
    by_action = {}
    by_event = {}
    by_point = {}
    for row in rows:
        action = row.get("action") or "unknown"
        by_action[action] = by_action.get(action, 0) + 1
        point_id = row.get("point_id") or "unknown"
        by_point[point_id] = by_point.get(point_id, 0) + 1
        for event_id in row.get("event_ids") or []:
            by_event[event_id] = by_event.get(event_id, 0) + 1

    inv = _load_investigations()
    invasions = _load_invasions().get("users", {})
    buildup_users = _load_buildup().get("users", {})
    users = sorted(set(inv.keys()) | set(invasions.keys()) | set(buildup_users.keys()))
    if user_id:
        users = [u for u in users if u == user_id]

    user_summaries = []
    for uid in users:
        investigated = inv.get(uid, [])
        invaded = invasions.get(uid, {}).get("invaded_ids", [])
        placements = buildup_users.get(uid, {}).get("placements", [])
        user_summaries.append({
            "user_id": uid,
            "investigated_count": len(investigated),
            "secured_count": len(invaded),
            "placement_count": len(placements),
            "pending_points": _compute_pending_buildup_points(uid),
        })

    return {
        "success": True,
        "user_id": user_id,
        "event_log_rows": len(rows),
        "actions": by_action,
        "events": by_event,
        "points": by_point,
        "users": user_summaries,
        "generated_at": _utc_now().isoformat(),
    }


@star_map_bp.route("/api/star-map/25/analytics", methods=["GET"])
def star_map_25_analytics():
    """Analytics summary for Star Map 25 actions, events, and user progress."""
    user_id = request.args.get("user_id")
    try:
        return jsonify(_star_map_25_analytics_payload(user_id=user_id)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@star_map_bp.route("/api/star-map/25/leaderboard", methods=["GET"])
def star_map_25_leaderboard():
    """Leaderboard ranked by secured systems, investigations, levels, placements, and pending yield."""
    try:
        limit = min(100, max(1, int(request.args.get("limit", 25))))
    except Exception:
        limit = 25
    try:
        data = _load_star_map_25()
        total_points = len(data.get("points", [])) or 25
        inv = _load_investigations()
        invasions = _load_invasions().get("users", {})
        buildup_users = _load_buildup().get("users", {})
        users = sorted(set(inv.keys()) | set(invasions.keys()) | set(buildup_users.keys()))
        rows = []
        for uid in users:
            investigated = inv.get(uid, [])
            invaded = invasions.get(uid, {}).get("invaded_ids", [])
            placements = buildup_users.get(uid, {}).get("placements", [])
            levels = _get_user_system_levels(uid)
            level_sum = sum(int(v or 0) for v in levels.values())
            pending = _compute_pending_buildup_points(uid)
            score = (len(invaded) * 1000) + (len(investigated) * 100) + (level_sum * 10) + len(placements) + pending
            rows.append({
                "user_id": uid,
                "score": round(score, 2),
                "investigated_count": len(investigated),
                "secured_count": len(invaded),
                "total_points": total_points,
                "level_sum": level_sum,
                "placement_count": len(placements),
                "pending_points": pending,
            })
        rows.sort(key=lambda r: (r["score"], r["secured_count"], r["investigated_count"]), reverse=True)
        for idx, row in enumerate(rows, start=1):
            row["rank"] = idx
        return jsonify({
            "success": True,
            "leaderboard": rows[:limit],
            "scoring": "secured*1000 + investigated*100 + level_sum*10 + placements + pending_points",
            "generated_at": _utc_now().isoformat(),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _star_map_25_agent_tools():
    return [
        {"name": "read_status", "method": "GET", "path": "/api/star-map/25/status", "mutates": False, "required": ["user_id"]},
        {"name": "read_point", "method": "GET", "path": "/api/star-map/25/point/{point_id}", "mutates": False, "required": ["point_id"]},
        {"name": "read_segmentum", "method": "GET", "path": "/api/star-map/25/segmentum/{segmentum}", "mutates": False, "required": ["segmentum"]},
        {"name": "read_analytics", "method": "GET", "path": "/api/star-map/25/analytics", "mutates": False, "required": []},
        {"name": "read_leaderboard", "method": "GET", "path": "/api/star-map/25/leaderboard", "mutates": False, "required": []},
        {"name": "investigate", "method": "POST", "path": "/api/star-map/25/investigate", "mutates": True, "required": ["user_id", "point_id", "approved"]},
        {"name": "build", "method": "POST", "path": "/api/star-map/25/build", "mutates": True, "required": ["user_id", "point_id", "planet", "building_id", "approved"]},
        {"name": "deploy", "method": "POST", "path": "/api/star-map/25/deploy", "mutates": True, "required": ["user_id", "point_id", "planet", "unit_id", "approved"]},
        {"name": "collect", "method": "POST", "path": "/api/star-map/25/collect", "mutates": True, "required": ["user_id", "approved"]},
        {"name": "invade", "method": "POST", "path": "/api/star-map/25/invade", "mutates": True, "required": ["user_id", "point_id", "unit_id", "approved"]},
    ]


@star_map_bp.route("/api/star-map/25/agent-tools", methods=["GET"])
def star_map_25_agent_tools():
    """Agent-safe capability map for Star Map 25. Mutating actions require explicit approved=true."""
    return jsonify({
        "success": True,
        "surface": "star_map_25",
        "safety": "Read tools are direct. Mutating tools require approved=true and use the same validation as UI endpoints.",
        "tools": _star_map_25_agent_tools(),
    }), 200


@star_map_bp.route("/api/star-map/25/agent-action", methods=["POST"])
def star_map_25_agent_action():
    """Execute an approved Star Map 25 agent action through the same route logic as the UI."""
    try:
        data = request.get_json() or {}
        action = (data.get("action") or "").strip()
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
        payload = dict(payload)
        payload.setdefault("user_id", data.get("user_id") or request.args.get("user_id") or "default_user")

        from flask import current_app
        from urllib.parse import quote
        safe_user_id = quote(str(payload.get("user_id", "default_user")), safe="")
        if action == "read_status":
            with current_app.test_request_context(
                "/api/star-map/25/status?user_id=" + safe_user_id,
                method="GET",
            ):
                return get_star_map_25_status()
        if action == "read_analytics":
            with current_app.test_request_context(
                "/api/star-map/25/analytics?user_id=" + safe_user_id,
                method="GET",
            ):
                return star_map_25_analytics()
        if action == "read_leaderboard":
            with current_app.test_request_context("/api/star-map/25/leaderboard", method="GET"):
                return star_map_25_leaderboard()
        if action == "read_point":
            point_id = payload.get("point_id")
            if not point_id:
                return jsonify({"success": False, "error": "point_id required"}), 400
            with current_app.test_request_context(
                "/api/star-map/25/point/%s?user_id=%s" % (quote(str(point_id), safe=""), safe_user_id),
                method="GET",
            ):
                return get_star_map_25_point(point_id)
        if action == "read_segmentum":
            segmentum = payload.get("segmentum")
            if not segmentum:
                return jsonify({"success": False, "error": "segmentum required"}), 400
            with current_app.test_request_context(
                "/api/star-map/25/segmentum/%s?user_id=%s" % (quote(str(segmentum), safe=""), safe_user_id),
                method="GET",
            ):
                return get_star_map_25_segmentum(segmentum)

        mutating = {
            "investigate": ("/api/star-map/25/investigate", investigate_star_map_25_point),
            "build": ("/api/star-map/25/build", build_star_map_25),
            "deploy": ("/api/star-map/25/deploy", deploy_star_map_25),
            "collect": ("/api/star-map/25/collect", collect_star_map_25_buildup),
            "invade": ("/api/star-map/25/invade", invade_star_map_25),
        }
        if action not in mutating:
            return jsonify({"success": False, "error": "Unknown action", "tools": _star_map_25_agent_tools()}), 400
        if data.get("approved") is not True and payload.get("approved") is not True:
            return jsonify({
                "success": False,
                "error": "Mutating Star Map 25 agent actions require approved=true",
                "action": action,
            }), 403

        path, handler = mutating[action]
        with current_app.test_request_context(path, method="POST", json=payload):
            return handler()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _star_map_25_openapi_spec():
    routes = [
        ("GET", "/api/star-map/25", "Full Star Map 25 data"),
        ("GET", "/api/star-map/25/point/{point_id}", "Single point with user state"),
        ("GET", "/api/star-map/25/segmentums", "All Segmentum progress summaries"),
        ("GET", "/api/star-map/25/segmentum/{segmentum}", "One Segmentum progress summary"),
        ("GET", "/api/star-map/25/status", "User progress, invasion state, trophies, crypto status"),
        ("POST", "/api/star-map/25/investigate", "Investigate one point and award game_points"),
        ("GET", "/api/star-map/25/buildings", "Building catalog"),
        ("GET", "/api/star-map/25/units", "Unit catalog"),
        ("GET", "/api/star-map/25/events", "Active/upcoming event windows"),
        ("GET", "/api/star-map/25/crypto", "MN2 in-game claim options"),
        ("POST", "/api/star-map/25/crypto/claim", "Claim eligible in-game MN2 reward"),
        ("GET", "/api/star-map/25/buildup", "Placements and pending buildup yield"),
        ("POST", "/api/star-map/25/build", "Place a building"),
        ("POST", "/api/star-map/25/deploy", "Deploy a unit"),
        ("POST", "/api/star-map/25/collect", "Collect pending buildup yield"),
        ("POST", "/api/star-map/25/invade", "Secure an investigated system with deployed unit"),
        ("GET", "/api/star-map/25/levels", "Computed system levels and daily reset"),
        ("GET", "/api/star-map/25/analytics", "Action/event analytics summary"),
        ("GET", "/api/star-map/25/leaderboard", "Star Map 25 leaderboard"),
        ("GET", "/api/star-map/25/health", "Data and writable-state health check"),
        ("GET", "/api/star-map/25/agent-tools", "Agent-safe capability map"),
        ("POST", "/api/star-map/25/agent-action", "Execute read or explicitly approved agent action"),
        ("GET", "/api/star-map/25/openapi", "This OpenAPI document"),
    ]
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "MasterNoder Star Map 25 API",
            "version": "2026-04-29",
            "description": "Star Map 25 gameplay, analytics, health, and agent-safe action surface.",
        },
        "paths": {
            path: {
                method.lower(): {
                    "summary": summary,
                    "responses": {
                        "200": {"description": "Success"},
                        "400": {"description": "Invalid input"},
                        "403": {"description": "Approval required"},
                        "404": {"description": "Not found"},
                        "500": {"description": "Server error"},
                    },
                }
            }
            for method, path, summary in routes
        },
    }


@star_map_bp.route("/api/star-map/25/openapi", methods=["GET"])
def star_map_25_openapi():
    """OpenAPI documentation for Star Map 25 endpoints."""
    return jsonify(_star_map_25_openapi_spec()), 200


def _load_agent_calendar():
    if os.path.exists(AGENT_CALENDAR_PATH):
        try:
            with open(AGENT_CALENDAR_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "appointments": [],
        "agents": [
            "content_generator_agent",
            "learning_agent",
            "analytics_agent",
            "reporter_agent",
        ],
    }


def _save_agent_calendar(data):
    try:
        os.makedirs(os.path.dirname(AGENT_CALENDAR_PATH), exist_ok=True)
        with open(AGENT_CALENDAR_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


@star_map_bp.route("/api/star-map/25/ai-hint", methods=["GET", "POST"])
def star_map_25_ai_hint():
    """Get 2–3 AI-generated tactical hints for Star Map 25 (levels, buildup, daily reset). Uses LLM when available."""
    user_id = request.args.get("user_id") or (request.get_json() or {}).get("user_id") or "default_user"
    try:
        inv = _load_investigations()
        investigated = inv.get(user_id, [])
        sm25 = _load_star_map_25()
        points_list = sm25.get("points", [])
        point_values = {p["id"]: p.get("point_value", 10) for p in points_list}
        total_earned = sum(
            _sm25_investigation_reward(point_values.get(pid, 10)) for pid in investigated
        )
        levels = _get_user_system_levels(user_id)
        max_level = _load_system_levels_config().get("max_level", 5)
        at_max = sum(1 for v in levels.values() if v >= max_level)
        pending = _compute_pending_buildup_points(user_id)
        next_reset_iso, in_bonus = _next_daily_reset_utc()
        wt = _compute_walkthrough_state(len(investigated))
        wt_level = wt.get("current_level", 0)
        context = (
            f"Star Map 25: {len(investigated)}/25 systems investigated, {total_earned} points earned. "
            f"Profile walkthrough tier {wt_level}/10. "
            f"{at_max} systems at max level ({max_level}). Pending collect: {pending} game_points. "
            f"Daily reset 2× bonus: {'active for 12h after midnight UTC' if in_bonus else 'next at midnight UTC'}."
        )
        hints = []
        provider = None
        try:
            from backend.services.llm_service import llm_service
            if llm_service and llm_service.is_available():
                from backend.services.llm_service import chat
                resp = chat(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a tactical coach for Star Map 25 (Imperium investigation grid). Give exactly 2 or 3 short, specific tips (one sentence each). Mention: which system to level next, when to collect, which building to build, or daily reset. Output only the tips, one per line, no numbering or bullets."
                        },
                        {"role": "user", "content": context}
                    ],
                    task_type="speed",
                    max_tokens=180,
                    temperature=0.7,
                )
                if resp and getattr(resp, "success", False) and getattr(resp, "content", ""):
                    provider = getattr(resp, "provider", None)
                    raw = (resp.content or "").strip()
                    for line in raw.split("\n"):
                        line = line.strip().lstrip("0123456789.-) ")
                        if line and len(line) > 10:
                            hints.append(line)
        except Exception:
            pass
        if not hints:
            if in_bonus and pending > 0:
                hints = ["Collect your buildup now—you're in the 2× bonus window.", "Level systems to 4+ to unlock Orbital Fortress and Sanctum."]
            elif at_max < len(levels) and len(levels) > 0:
                hints = ["Build more structures in investigated systems to reach level 5 (Dominion).", "Daily reset at midnight UTC: high-level structures earn 2× for 12h."]
            else:
                hints = ["Investigate more systems to unlock building and deployment.", "After investigating, build Outposts and deploy units to earn points over time."]
        return jsonify({
            "success": True,
            "user_id": user_id,
            "hints": hints[:3],
            "provider": provider,
            "context_summary": context,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "hints": []}), 500


@star_map_bp.route("/api/star-map/25/ai-guide", methods=["GET", "POST"])
def star_map_25_ai_guide():
    """
    AI explains upcoming / unknown walkthrough features using canonical proof docs.
    Response always includes full readable proofs beside the narrative (documentation).
    """
    user_id = request.args.get("user_id") or (request.get_json() or {}).get("user_id") or "default_user"
    focus = (request.args.get("focus") or (request.get_json() or {}).get("focus") or "").strip()
    try:
        inv = _load_investigations()
        investigated = inv.get(user_id, [])
        inv_count = len(investigated)
        proof_bundle = _load_ai_proof_docs()
        proofs = proof_bundle.get("proofs", [])
        locked = _locked_walkthrough_rows(inv_count)
        wt = _compute_walkthrough_state(inv_count)
        wt_level = wt.get("current_level", 0)

        proof_text = "\n".join(
            f"[{p.get('id', '')}] {p.get('title', '')}: {p.get('body', '')} Refs: {', '.join(p.get('refs') or [])}"
            for p in proofs
        )
        locked_summary = "\n".join(
            f"- Tier {r.get('level')}: {r.get('title')} — need {r.get('min_investigations')} investigations "
            f"({r.get('investigations_short', 0)} more). Feature: {r.get('feature', '')}"
            for r in locked[:10]
        )
        if not locked_summary:
            locked_summary = "All walkthrough tiers unlocked (25/25 investigations)."

        narrative = None
        provider = None
        try:
            from backend.services.llm_service import llm_service
            if llm_service and llm_service.is_available():
                from backend.services.llm_service import chat
                sys_msg = (
                    "You are the Star Map 25 Field Strategist (Warhammer 40,000 Imperium investigation grid). "
                    "Explain ONLY upcoming or unclear features the player has not unlocked yet, using the LOCKED FEATURES list. "
                    "Ground every mechanic in the CANONICAL FACTS; do not invent APIs, multipliers, or files. "
                    "Write 2 short paragraphs (or 5-7 bullet lines). Mention what to do next (investigate, build, collect, open 3D/4D, planet chips). "
                    "You may reference proof ids in parentheses like (mult) or (planet_intel)."
                )
                user_msg = (
                    f"User_id={user_id}. Investigated {inv_count}/25. Walkthrough tier {wt_level}/10.\n"
                    f"FOCUS: {focus or 'general'}\n\n"
                    f"LOCKED FEATURES:\n{locked_summary}\n\n"
                    f"CANONICAL FACTS:\n{proof_text}"
                )
                resp = chat(
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    task_type="speed",
                    max_tokens=500,
                    temperature=0.55,
                )
                if resp and getattr(resp, "success", False) and getattr(resp, "content", ""):
                    narrative = (resp.content or "").strip()
                    provider = getattr(resp, "provider", None)
        except Exception:
            pass

        if not narrative:
            next_line = locked[0] if locked else None
            if next_line:
                narrative = (
                    f"You have {inv_count}/25 investigations and walkthrough tier {wt_level}/10. "
                    f"Next: tier {next_line.get('level')} — {next_line.get('title')}. "
                    f"Need {next_line.get('investigations_short', 0)} more investigation(s) to unlock: {next_line.get('feature', '')}. "
                    f"See readable proofs for APIs and formulas."
                )
            else:
                narrative = (
                    f"Map cleared at {inv_count}/25. Walkthrough tier {wt_level}. "
                    "Use proofs for buildup, collect, and system levels APIs if you extend play."
                )

        hints = []
        for line in narrative.replace("\r", "").split("\n"):
            line = line.strip().lstrip("•-* ")
            if line and len(hints) < 8:
                hints.append(line)
        if len(hints) <= 1 and narrative:
            hints = [narrative]

        return jsonify({
            "success": True,
            "user_id": user_id,
            "narrative": narrative,
            "hints": hints[:8],
            "locked_features": locked,
            "walkthrough_level": wt_level,
            "investigated_count": inv_count,
            "proofs": proofs,
            "proof_doc_title": proof_bundle.get("title", ""),
            "proof_doc_description": proof_bundle.get("description", ""),
            "provider": provider,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "proofs": [], "narrative": "", "hints": []}), 500


@star_map_bp.route("/api/agent-calendar", methods=["GET", "POST"])
def agent_calendar():
    """GET: list appointments (optional agent_id, from_ts, to_ts). POST: create appointment (agent_id, task, scheduled_at, title)."""
    try:
        if request.method == "POST":
            data = request.get_json() or {}
            agent_id = (data.get("agent_id") or "").strip()
            task = (data.get("task") or "").strip()
            scheduled_at = (data.get("scheduled_at") or "").strip()
            title = (data.get("title") or (task[:50] if task else "Appointment")).strip()
            if not agent_id or not scheduled_at:
                return jsonify({"success": False, "error": "agent_id and scheduled_at required"}), 400
            cal = _load_agent_calendar()
            if agent_id not in (cal.get("agents") or []):
                cal.setdefault("agents", []).append(agent_id)
            import uuid
            from datetime import datetime, timezone
            appointment = {
                "id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "task": task or title,
                "title": title,
                "scheduled_at": scheduled_at,
                "status": "scheduled",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            cal.setdefault("appointments", []).append(appointment)
            _save_agent_calendar(cal)
            return jsonify({"success": True, "appointment": appointment}), 201
        data = _load_agent_calendar()
        agent_id = request.args.get("agent_id")
        from_ts = request.args.get("from_ts")
        to_ts = request.args.get("to_ts")
        appointments = list(data.get("appointments", []))
        if agent_id:
            appointments = [a for a in appointments if a.get("agent_id") == agent_id]
        if from_ts:
            appointments = [a for a in appointments if (a.get("scheduled_at") or "") >= from_ts]
        if to_ts:
            appointments = [a for a in appointments if (a.get("scheduled_at") or "") <= to_ts]
        appointments.sort(key=lambda a: a.get("scheduled_at", ""))
        return jsonify({
            "success": True,
            "appointments": appointments,
            "agents": data.get("agents", []),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
