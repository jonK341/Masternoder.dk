"""Landing monitor action bus — learn, store, and movie-style reel sync."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ACTIONS_PATH = os.path.join(_BASE, "data", "landing_monitor_actions.json")
_LEARN_PATH = os.path.join(_BASE, "data", "landing_monitor_learning.json")

# Same-category cinematic FX (maps to canvas lightshow ids).
CATEGORY_FX: Dict[str, Dict[str, Any]] = {
    "wallet": {
        "lightshow": "spectrum",
        "title": "Wallet spectrum",
        "explain": "Spectrum bars punch on wallet/MN2 actions — deposit energy as green peaks.",
        "color": "#00ff88",
        "bars": 4,
        "sound": "coin_sparkle",
    },
    "battle": {
        "lightshow": "chase",
        "title": "Battle chase",
        "explain": "Chase nodes ring the bezel for battle/game hits — one step per beat.",
        "color": "#ff5a6a",
        "bars": 6,
        "sound": "impact_blast",
    },
    "generator": {
        "lightshow": "wave",
        "title": "Generator waves",
        "explain": "Cyan waves roll for video/generator events — scene-change ripples.",
        "color": "#00d4ff",
        "bars": 5,
        "sound": "whoosh_rise",
    },
    "profit": {
        "lightshow": "pulse",
        "title": "Profit pulse",
        "explain": "Deep pulse for profit/exchange fills — heartbeat of the treasury.",
        "color": "#ffd166",
        "bars": 4,
        "sound": "chime_cash",
    },
    "social": {
        "lightshow": "rainbow",
        "title": "Social rainbow",
        "explain": "Rainbow wash for social/Discord posts — community color sweep.",
        "color": "#c77dff",
        "bars": 5,
        "sound": "bubble_ping",
    },
    "system": {
        "lightshow": "pulse",
        "title": "System pulse",
        "explain": "Neutral pulse for ops/system ticks — keep the lobby honest.",
        "color": "#9aa4b2",
        "bars": 3,
        "sound": "tick_blip",
    },
}

_TYPE_TO_CATEGORY = (
    (("wallet", "mn2", "deposit", "withdraw", "shop"), "wallet"),
    (("battle", "game", "quest", "trophy", "hunter"), "battle"),
    (("generator", "video", "gallery", "encode", "clip"), "generator"),
    (("profit", "exchange", "arb", "grid", "daemon", "trade"), "profit"),
    (("social", "discord", "news", "fanout", "chat"), "social"),
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return dict(default)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def _write(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def categorize(event_type: str, channel: Optional[str] = None, text: Optional[str] = None) -> str:
    blob = " ".join([event_type or "", channel or "", text or ""]).lower()
    for keys, cat in _TYPE_TO_CATEGORY:
        if any(k in blob for k in keys):
            return cat
    return "system"


def _empty_learning() -> Dict[str, Any]:
    return {
        "updated_at": None,
        "total_actions": 0,
        "categories": {},
        "features": {},
        "last_action_id": None,
    }


def _learn_inplace(learn: Dict[str, Any], action: Dict[str, Any]) -> None:
    cat = str(action.get("category") or "system")
    cats = learn.setdefault("categories", {})
    row = cats.setdefault(
        cat,
        {"count": 0, "novelty": 1.0, "last_ts": None, "fx": CATEGORY_FX.get(cat, CATEGORY_FX["system"])},
    )
    row["count"] = int(row.get("count") or 0) + 1
    # Novelty decays with repetition; floors at 0.15
    prev = float(row.get("novelty") or 1.0)
    row["novelty"] = max(0.15, round(prev * 0.92, 4))
    row["last_ts"] = action.get("ts")
    row["fx"] = CATEGORY_FX.get(cat, CATEGORY_FX["system"])

    features = learn.setdefault("features", {})
    feat_key = f"{cat}:{(action.get('type') or 'event')}"
    frow = features.setdefault(feat_key, {"count": 0, "weight": 0.5, "title": action.get("title")})
    frow["count"] = int(frow.get("count") or 0) + 1
    # Learning weight rises toward 1.0 as the action repeats (familiar pattern).
    frow["weight"] = min(1.0, round(0.5 + 0.08 * frow["count"], 4))
    frow["title"] = action.get("title") or frow.get("title")
    frow["last_ts"] = action.get("ts")

    learn["total_actions"] = int(learn.get("total_actions") or 0) + 1
    learn["last_action_id"] = action.get("id")
    learn["updated_at"] = _iso()


def record_action(
    event_type: str,
    *,
    title: Optional[str] = None,
    text: Optional[str] = None,
    channel: Optional[str] = None,
    user_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    source: str = "manual",
    ts: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist one action, update learning, return stored row + fx."""
    et = (event_type or "event").strip()[:80]
    cat = category or categorize(et, channel, text or title)
    fx = dict(CATEGORY_FX.get(cat, CATEGORY_FX["system"]))
    stamp = ts or _iso()
    action = {
        "id": f"lma_{uuid.uuid4().hex[:12]}",
        "ts": stamp,
        "type": et,
        "category": cat,
        "title": (title or text or et.replace("_", " ").title())[:160],
        "text": (text or title or et)[:280],
        "channel": channel,
        "user_id": user_id,
        "source": source,
        "payload": payload or {},
        "fx": fx,
        "played": False,
    }
    with _LOCK:
        store = _read(_ACTIONS_PATH, {"actions": [], "updated_at": None})
        actions = store.get("actions") if isinstance(store.get("actions"), list) else []
        # Idempotent when the same activity stamp already landed.
        for existing in actions:
            if (
                isinstance(existing, dict)
                and existing.get("type") == et
                and existing.get("ts") == stamp
            ):
                return {"success": True, "action": existing, "learning": {"category": cat, "fx": fx}, "deduped": True}
        actions.insert(0, action)
        store["actions"] = actions[:400]
        store["updated_at"] = _iso()
        _write(_ACTIONS_PATH, store)

        learn = _read(_LEARN_PATH, _empty_learning())
        _learn_inplace(learn, action)
        _write(_LEARN_PATH, learn)

    return {"success": True, "action": action, "learning": {"category": cat, "fx": fx}}


def sync_from_activity(*, limit: int = 40) -> Dict[str, Any]:
    """Pull recent activity_events into the monitor store (idempotent by ts+type)."""
    try:
        from backend.services.activity_events_service import recent as activity_recent
    except Exception as exc:
        return {"success": False, "error": str(exc)[:160], "imported": 0}

    rows = activity_recent(limit=limit)
    imported = 0
    with _LOCK:
        store = _read(_ACTIONS_PATH, {"actions": [], "updated_at": None})
        actions = store.get("actions") if isinstance(store.get("actions"), list) else []
        seen = {(a.get("type"), a.get("ts")) for a in actions if isinstance(a, dict)}
        learn = _read(_LEARN_PATH, _empty_learning())
        for row in reversed(rows):  # oldest first so learning order is chronological
            if not isinstance(row, dict):
                continue
            key = (row.get("type"), row.get("ts"))
            if key in seen:
                continue
            et = str(row.get("type") or "event")
            cat = categorize(et, row.get("channel"), row.get("text"))
            fx = dict(CATEGORY_FX.get(cat, CATEGORY_FX["system"]))
            action = {
                "id": f"lma_{uuid.uuid4().hex[:12]}",
                "ts": row.get("ts") or _iso(),
                "type": et,
                "category": cat,
                "title": (row.get("text") or et.replace("_", " ").title())[:160],
                "text": (row.get("text") or et)[:280],
                "channel": row.get("channel"),
                "user_id": row.get("user_id"),
                "source": "activity_events",
                "payload": row.get("payload") or {},
                "fx": fx,
                "played": False,
            }
            actions.insert(0, action)
            seen.add(key)
            _learn_inplace(learn, action)
            imported += 1
        store["actions"] = actions[:400]
        store["updated_at"] = _iso()
        _write(_ACTIONS_PATH, store)
        _write(_LEARN_PATH, learn)
    return {"success": True, "imported": imported, "total": len(actions)}


def list_actions(*, limit: int = 40, category: Optional[str] = None, unplayed_only: bool = False) -> Dict[str, Any]:
    safe = max(1, min(int(limit or 40), 120))
    with _LOCK:
        store = _read(_ACTIONS_PATH, {"actions": [], "updated_at": None})
        actions = [a for a in (store.get("actions") or []) if isinstance(a, dict)]
    if category:
        actions = [a for a in actions if a.get("category") == category]
    if unplayed_only:
        actions = [a for a in actions if not a.get("played")]
    return {
        "success": True,
        "actions": actions[:safe],
        "updated_at": store.get("updated_at"),
        "count": len(actions[:safe]),
    }


def learning_snapshot() -> Dict[str, Any]:
    with _LOCK:
        learn = _read(_LEARN_PATH, _empty_learning())
    return {"success": True, "learning": learn}


def build_reel(*, limit: int = 24, prefer_unplayed: bool = True) -> Dict[str, Any]:
    """Ordered movie reel: unplayed first, then by learning weight / novelty."""
    with _LOCK:
        store = _read(_ACTIONS_PATH, {"actions": [], "updated_at": None})
        learn = _read(_LEARN_PATH, _empty_learning())
        actions = [a for a in (store.get("actions") or []) if isinstance(a, dict)]

    features = learn.get("features") if isinstance(learn.get("features"), dict) else {}
    cats = learn.get("categories") if isinstance(learn.get("categories"), dict) else {}

    def score(a: Dict[str, Any]) -> tuple:
        cat = str(a.get("category") or "system")
        feat_key = f"{cat}:{(a.get('type') or 'event')}"
        weight = float((features.get(feat_key) or {}).get("weight") or 0.5)
        novelty = float((cats.get(cat) or {}).get("novelty") or 0.5)
        unplayed = 0 if a.get("played") else 1
        return (unplayed if prefer_unplayed else 0, weight + novelty, a.get("ts") or "")

    ordered = sorted(actions, key=score, reverse=True)
    safe = max(1, min(int(limit or 24), 60))
    reel = []
    for a in ordered[:safe]:
        cat = str(a.get("category") or "system")
        fx = dict(a.get("fx") or CATEGORY_FX.get(cat, CATEGORY_FX["system"]))
        reel.append(
            {
                **a,
                "fx": fx,
                "scene_ms": int(fx.get("bars") or 4) * 333,  # ~bars at 180 BPM
            }
        )
    return {
        "success": True,
        "reel": reel,
        "count": len(reel),
        "bpm": 180,
        "learning": {
            "total_actions": learn.get("total_actions") or 0,
            "categories": cats,
        },
        "updated_at": _iso(),
    }


def mark_played(action_ids: List[str]) -> Dict[str, Any]:
    ids = {str(i) for i in (action_ids or []) if i}
    if not ids:
        return {"success": True, "marked": 0}
    marked = 0
    with _LOCK:
        store = _read(_ACTIONS_PATH, {"actions": [], "updated_at": None})
        actions = store.get("actions") if isinstance(store.get("actions"), list) else []
        for a in actions:
            if isinstance(a, dict) and a.get("id") in ids and not a.get("played"):
                a["played"] = True
                a["played_at"] = _iso()
                marked += 1
        store["actions"] = actions
        store["updated_at"] = _iso()
        _write(_ACTIONS_PATH, store)
    return {"success": True, "marked": marked}
