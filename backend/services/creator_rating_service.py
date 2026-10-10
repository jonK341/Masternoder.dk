"""
Creator rating system — pay MN2 crypto to rate music/video tracks.

Primary app purpose: community rates creator content; creators earn MN2 share.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CFG_PATH = os.path.join(_BASE, "data", "creator_config.json")
_RATINGS_PATH = os.path.join(_BASE, "data", "creator_ratings.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    os.replace(tmp, path)


def _rating_config() -> Dict[str, Any]:
    cfg = _read_json(_CFG_PATH)
    return cfg.get("rating") if isinstance(cfg.get("rating"), dict) else {}


def _load_ratings() -> dict:
    with _LOCK:
        return _read_json(_RATINGS_PATH)


def _save_ratings(data: dict) -> None:
    with _LOCK:
        _write_json(_RATINGS_PATH, data)


def get_rating_config() -> Dict[str, Any]:
    rc = _rating_config()
    return {
        "success": True,
        "enabled": bool(rc.get("enabled", True)),
        "cost_mn2": float(rc.get("cost_mn2") or 0.01),
        "creator_share": float(rc.get("creator_share") or 0.7),
        "min_score": int(rc.get("min_score") or 1),
        "max_score": int(rc.get("max_score") or 5),
        "require_payment": bool(rc.get("require_payment", True)),
        "featured_min_avg": float(rc.get("featured_min_avg") or 4.0),
    }


def _update_track_rating(track_id: str, avg: float, count: int) -> None:
    from backend.services.super_encoder_service import _load_tracks, _save_tracks
    catalog = _load_tracks()
    tracks = catalog.get("tracks") or []
    for t in tracks:
        if t.get("id") == track_id:
            t["avg_rating"] = round(avg, 2)
            t["rating_count"] = count
            t["updated_at"] = _iso()
            break
    catalog["tracks"] = tracks
    _save_tracks(catalog)


def rate_track(
    rater_id: str,
    track_id: str,
    score: int,
    pay_with_mn2: bool = True,
) -> Dict[str, Any]:
    """Rate a track with optional MN2 payment. Credits creator their share."""
    rc = _rating_config()
    if not rc.get("enabled", True):
        return {"success": False, "error": "Rating disabled"}

    min_s = int(rc.get("min_score") or 1)
    max_s = int(rc.get("max_score") or 5)
    score = int(score)
    if score < min_s or score > max_s:
        return {"success": False, "error": f"Score must be {min_s}–{max_s}"}

    from backend.services.super_encoder_service import get_track
    track = get_track(track_id)
    if not track:
        return {"success": False, "error": "Track not found"}

    creator_id = track.get("user_id") or "unknown"
    if rater_id == creator_id:
        return {"success": False, "error": "Cannot rate your own track"}

    cost = float(rc.get("cost_mn2") or 0.01)
    creator_share = float(rc.get("creator_share") or 0.7)
    creator_earn = round(cost * creator_share, 8)

    data = _load_ratings()
    votes = data.get("user_votes") or {}
    vote_key = f"{rater_id}:{track_id}"
    if vote_key in votes:
        return {"success": False, "error": "Already rated this track", "existing_score": votes[vote_key].get("score")}

    if pay_with_mn2 and rc.get("require_payment", True) and cost > 0:
        try:
            from backend.services.generator_mn2_service import _debit, _credit
            debit = _debit(rater_id, cost, {"source": "creator_rating", "track_id": track_id, "score": score})
            if not debit.get("success"):
                return debit
            if creator_earn > 0:
                _credit(creator_id, creator_earn, "creator_rating_earn", {
                    "track_id": track_id, "rater_id": rater_id, "score": score,
                })
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    ratings = data.get("ratings") or {}
    track_ratings: List[dict] = ratings.get(track_id) or []
    track_ratings.append({
        "rater_id": rater_id,
        "score": score,
        "paid_mn2": cost if pay_with_mn2 else 0,
        "created_at": _iso(),
    })
    ratings[track_id] = track_ratings
    votes[vote_key] = {"score": score, "created_at": _iso()}
    data["ratings"] = ratings
    data["user_votes"] = votes
    _save_ratings(data)

    scores = [r["score"] for r in track_ratings]
    avg = sum(scores) / len(scores) if scores else 0
    _update_track_rating(track_id, avg, len(scores))

    out = {
        "success": True,
        "track_id": track_id,
        "score": score,
        "cost_mn2": cost if pay_with_mn2 else 0,
        "creator_earned_mn2": creator_earn,
        "avg_rating": round(avg, 2),
        "rating_count": len(scores),
    }
    try:
        from backend.services.micro_tx_hooks import try_micro_tx_reward

        micro = try_micro_tx_reward(
            rater_id,
            "creator_rating",
            idempotency_key=f"creator_rating:{rater_id}:{track_id}",
            reason="Track rating bonus",
            metadata={"track_id": track_id, "score": score},
        )
        if micro:
            out["micro_tx_reward"] = micro
    except Exception:
        pass
    return out


def get_track_ratings(track_id: str) -> Dict[str, Any]:
    data = _load_ratings()
    track_ratings = (data.get("ratings") or {}).get(track_id) or []
    scores = [r["score"] for r in track_ratings]
    avg = sum(scores) / len(scores) if scores else 0
    return {
        "success": True,
        "track_id": track_id,
        "ratings": track_ratings[-20:],
        "avg_rating": round(avg, 2),
        "rating_count": len(scores),
    }


def get_featured_tracks(limit: int = 20) -> Dict[str, Any]:
    """Top-rated tracks for the rating feed."""
    rc = _rating_config()
    min_avg = float(rc.get("featured_min_avg") or 4.0)
    min_count = int(rc.get("featured_min_ratings") or 3)
    from backend.services.super_encoder_service import list_tracks
    all_tracks = list_tracks(limit=125).get("tracks") or []
    featured = [
        t for t in all_tracks
        if float(t.get("avg_rating") or 0) >= min_avg
        and int(t.get("rating_count") or 0) >= min_count
        and t.get("status") == "completed"
    ]
    featured.sort(key=lambda x: (float(x.get("avg_rating") or 0), int(x.get("rating_count") or 0)), reverse=True)
    return {"success": True, "featured": featured[:limit], "count": len(featured)}
