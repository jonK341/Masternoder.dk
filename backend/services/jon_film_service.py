"""Jon Film — actor appointments, agent×camgirl stages, leveling (+1 / 20 assignments)."""
from __future__ import annotations

import json
import os
import random
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ACTORS_PATH = os.path.join(_BASE, "data", "jon_film_actors.json")
_APPTS_PATH = os.path.join(_BASE, "data", "jon_film_appointments.json")
_LEVELS_PATH = os.path.join(_BASE, "data", "jon_film_actor_levels.json")

MOVIE_TITLE = "Jon Film"
ASSIGNMENTS_PER_LEVEL = 20
DAILY_APPOINTMENTS = 10

DEFAULT_ACTORS = [
    {"id": "actor_jon", "name": "Jon", "role": "lead", "performer_id": "performer_nova", "agent_id": "camgirl_agent_nova"},
    {"id": "actor_nova", "name": "Nova Star", "role": "host", "performer_id": "performer_nova", "agent_id": "camgirl_agent_nova"},
    {"id": "actor_luna", "name": "Luna Eclipse", "role": "co-star", "performer_id": "performer_luna", "agent_id": "camgirl_agent_luna"},
    {"id": "actor_ember", "name": "Ember Blaze", "role": "battlefield_comm", "performer_id": "performer_ember", "agent_id": "camgirl_agent_ember"},
    {"id": "actor_iris", "name": "Iris Prism", "role": "stage_director", "performer_id": "performer_iris", "agent_id": "camgirl_agent_iris"},
    {"id": "actor_venus", "name": "Venus", "role": "finale_host", "performer_id": "performer_venus", "agent_id": "camgirl_agent_venus"},
]

STAGE_KINDS = (
    "battlefield_3500_briefing",
    "matrix_network_rail",
    "daemon_desk_duet",
    "lobby_pipeline_cut",
    "comm_line_relay",
    "camgirl_stage_live",
    "war_zone_recon",
    "appointment_rehearsal",
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def _level_for(assignments: int) -> int:
    return 1 + max(0, int(assignments)) // ASSIGNMENTS_PER_LEVEL


def ensure_actors() -> List[Dict[str, Any]]:
    with _LOCK:
        doc = _read(_ACTORS_PATH, {})
        actors = doc.get("actors") if isinstance(doc, dict) else None
        if not isinstance(actors, list) or not actors:
            actors = list(DEFAULT_ACTORS)
            _write(
                _ACTORS_PATH,
                {
                    "movie": MOVIE_TITLE,
                    "updated_at": _iso(),
                    "actors": actors,
                },
            )
        return actors


def _levels_doc() -> Dict[str, Any]:
    doc = _read(_LEVELS_PATH, {})
    if not isinstance(doc, dict):
        doc = {}
    levels = doc.get("levels") if isinstance(doc.get("levels"), dict) else {}
    return {"updated_at": doc.get("updated_at"), "levels": levels}


def get_actor_levels() -> Dict[str, Any]:
    actors = ensure_actors()
    doc = _levels_doc()
    levels = doc["levels"]
    out = []
    for actor in actors:
        aid = actor["id"]
        row = levels.get(aid) if isinstance(levels.get(aid), dict) else {}
        assignments = int(row.get("assignments") or 0)
        out.append(
            {
                **actor,
                "assignments": assignments,
                "level": _level_for(assignments),
                "next_level_in": ASSIGNMENTS_PER_LEVEL - (assignments % ASSIGNMENTS_PER_LEVEL),
                "movie": MOVIE_TITLE,
            }
        )
    return {
        "success": True,
        "movie": MOVIE_TITLE,
        "assignments_per_level": ASSIGNMENTS_PER_LEVEL,
        "actors": out,
        "updated_at": doc.get("updated_at") or _iso(),
    }


def _credit_assignment_unlocked(actor_id: str, *, amount: int = 1, reason: str = "appointment") -> Dict[str, Any]:
    doc = _levels_doc()
    levels = doc["levels"]
    row = dict(levels.get(actor_id) or {})
    before = int(row.get("assignments") or 0)
    after = before + max(1, int(amount))
    row.update(
        {
            "assignments": after,
            "level": _level_for(after),
            "last_reason": reason,
            "updated_at": _iso(),
        }
    )
    levels[actor_id] = row
    payload = {"updated_at": _iso(), "levels": levels}
    _write(_LEVELS_PATH, payload)
    return {"success": True, "actor_id": actor_id, "before": before, "after": after, "level": row["level"]}


def credit_assignment(actor_id: str, *, amount: int = 1, reason: str = "appointment") -> Dict[str, Any]:
    with _LOCK:
        return _credit_assignment_unlocked(actor_id, amount=amount, reason=reason)


def list_appointments(*, limit: int = 40, day: Optional[str] = None) -> Dict[str, Any]:
    doc = _read(_APPTS_PATH, {})
    rows = doc.get("appointments") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        rows = []
    if day:
        rows = [r for r in rows if str(r.get("day") or "") == day]
    rows = sorted(rows, key=lambda r: str(r.get("starts_at") or ""), reverse=False)
    return {
        "success": True,
        "movie": MOVIE_TITLE,
        "count": len(rows[:limit]),
        "appointments": rows[:limit],
        "generated_at": doc.get("generated_at") if isinstance(doc, dict) else None,
        "batch_id": doc.get("batch_id") if isinstance(doc, dict) else None,
    }


def generate_daily_appointments(*, force: bool = False, count: int = DAILY_APPOINTMENTS) -> Dict[str, Any]:
    """Fresh 10 different appointments for Jon Film actors — called by daily cron."""
    actors = ensure_actors()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _LOCK:
        existing = _read(_APPTS_PATH, {})
        if (
            not force
            and isinstance(existing, dict)
            and existing.get("day") == today
            and isinstance(existing.get("appointments"), list)
            and len(existing["appointments"]) >= count
        ):
            return {
                "success": True,
                "reused": True,
                "day": today,
                "batch_id": existing.get("batch_id"),
                "count": len(existing["appointments"]),
                "appointments": existing["appointments"],
            }

        rng = random.Random(f"{today}:{uuid.uuid4().hex}")
        batch_id = f"jonfilm_{today.replace('-', '')}_{rng.randint(1000, 9999)}"
        base = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
        appts: List[Dict[str, Any]] = []
        used_titles = set()
        for i in range(max(1, int(count))):
            actor = actors[i % len(actors)]
            stage = STAGE_KINDS[i % len(STAGE_KINDS)]
            title = f"{MOVIE_TITLE} · {stage.replace('_', ' ')} · take {i + 1}"
            while title in used_titles:
                title = f"{title} · {rng.randint(10, 99)}"
            used_titles.add(title)
            starts = base + timedelta(hours=i, minutes=rng.randint(0, 25))
            ends = starts + timedelta(minutes=35 + rng.randint(0, 20))
            appt = {
                "id": f"appt_{uuid.uuid4().hex[:10]}",
                "batch_id": batch_id,
                "day": today,
                "movie": MOVIE_TITLE,
                "title": title,
                "stage": stage,
                "theme": "war_battlefield_3500",
                "year": 3500,
                "actor_id": actor["id"],
                "actor_name": actor["name"],
                "performer_id": actor.get("performer_id"),
                "agent_id": actor.get("agent_id"),
                "comm_line": f"COMM-{3500 + i}-{rng.randint(10, 99)}",
                "starts_at": starts.isoformat().replace("+00:00", "Z"),
                "ends_at": ends.isoformat().replace("+00:00", "Z"),
                "status": "scheduled",
                "assignment_credited": False,
            }
            appts.append(appt)
            _credit_assignment_unlocked(actor["id"], amount=1, reason=f"daily_appt:{batch_id}")

        for a in appts:
            a["assignment_credited"] = True

        payload = {
            "movie": MOVIE_TITLE,
            "day": today,
            "batch_id": batch_id,
            "generated_at": _iso(),
            "fresh": True,
            "count": len(appts),
            "appointments": appts,
        }
        _write(_APPTS_PATH, payload)
        return {"success": True, "reused": False, **payload}


def calendar_snapshot() -> Dict[str, Any]:
    levels = get_actor_levels()
    appts = list_appointments(limit=30)
    return {
        "success": True,
        "movie": MOVIE_TITLE,
        "theme": "war_battlefield_3500",
        "year": 3500,
        "assignments_per_level": ASSIGNMENTS_PER_LEVEL,
        "actors": levels.get("actors") or [],
        "appointments": appts.get("appointments") or [],
        "batch_id": appts.get("batch_id"),
        "generated_at": appts.get("generated_at"),
        "updated_at": _iso(),
    }
