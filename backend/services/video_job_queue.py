"""
Priority video generation queue — optional scheduler to reduce uWSGI saturation.

Enable with VIDEO_JOB_QUEUE=1 or data/generator_config.json {"queue_enabled": true}.
"""
from __future__ import annotations

import heapq
import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

_LOCK = threading.Lock()
_QUEUE: List[Tuple[int, float, str, Dict[str, Any]]] = []
_PROCESSING = False
_WORKER_STARTED = False
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "generator_config.json")
_STATE_PATH = os.path.join(_BASE, "data", "video_job_queue.json")


def _load_config() -> Dict[str, Any]:
    defaults = {
        "queue_enabled": os.environ.get("VIDEO_JOB_QUEUE", "").strip().lower() in ("1", "true", "yes"),
        "max_concurrent": int(os.environ.get("VIDEO_JOB_MAX_CONCURRENT", "1") or 1),
        "base_priority": 100,
        "shop_booster_bonus": 50,
        "mn2_paid_bonus": 30,
    }
    if os.path.isfile(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            if isinstance(raw, dict):
                q = raw.get("queue") if isinstance(raw.get("queue"), dict) else raw
                defaults.update({k: v for k, v in q.items() if v is not None})
        except Exception:
            pass
    defaults["max_concurrent"] = max(1, min(int(defaults.get("max_concurrent") or 1), 4))
    return defaults


def _priority_for_user(user_id: str, config: Dict[str, Any]) -> int:
    score = int(config.get("base_priority") or 100)
    uid = str(user_id or "").strip()
    if not uid or uid == "default_user":
        return score + 20
    try:
        from backend.services.unified_points_database import unified_points_db

        pts = unified_points_db.get_all_points(uid)
        systems = pts.get("systems") if isinstance(pts.get("systems"), dict) else {}
        until = systems.get("gen_priority_until") or pts.get("points", {}).get("gen_priority_until")
        if until:
            from datetime import datetime, timezone

            try:
                exp = datetime.fromisoformat(str(until).replace("Z", "+00:00"))
                if exp > datetime.now(timezone.utc):
                    score -= int(config.get("shop_booster_bonus") or 50)
            except Exception:
                pass
    except Exception:
        pass
    return score


def _save_state(active: int, queued: int) -> None:
    try:
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        with open(_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({"active": active, "queued": queued, "ts": time.time()}, f)
    except Exception:
        pass


def enqueue(
    doc_id: str,
    job_config: Dict[str, Any],
    runner: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Queue or run immediately. Default runner: generator_shared.start_video_generation.
    Lower priority number = runs sooner.
    """
    cfg = _load_config()

    def _run(did: str, conf: Dict[str, Any]) -> None:
        if runner is not None:
            runner(did, conf)
            return
        from backend.routes.generator_shared import start_video_generation
        start_video_generation(did, conf)

    if not cfg.get("queue_enabled"):
        _run(doc_id, job_config)
        return {"success": True, "queued": False, "documentary_id": doc_id, "position": 0}

    uid = str(job_config.get("user_id") or "")
    pri = _priority_for_user(uid, cfg)
    with _LOCK:
        heapq.heappush(_QUEUE, (pri, time.time(), doc_id, job_config))
        pos = len(_QUEUE)
        _save_state(0, pos)
    global _RUNNER_OVERRIDE
    if runner is not None:
        _RUNNER_OVERRIDE = runner
    _ensure_worker()
    return {"success": True, "queued": True, "documentary_id": doc_id, "position": pos, "priority": pri}


_RUNNER_OVERRIDE: Optional[Callable[[str, Dict[str, Any]], None]] = None


def queue_status(user_id: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        queued = len(_QUEUE)
    active = 0
    if os.path.isfile(_STATE_PATH):
        try:
            with open(_STATE_PATH, "r", encoding="utf-8") as f:
                active = int(json.load(f).get("active") or 0)
        except Exception:
            pass
    position = None
    if user_id:
        uid = str(user_id).strip()
        with _LOCK:
            sorted_q = sorted(_QUEUE)
            for i, (_, _, _, job_config) in enumerate(sorted_q):
                if isinstance(job_config, dict) and str(job_config.get("user_id") or "") == uid:
                    position = i + 1
                    break
    return {"success": True, "queued": queued, "active": active, "your_position": position}


def _ensure_worker() -> None:
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    _WORKER_STARTED = True
    t = threading.Thread(target=_worker_loop, name="video-job-queue", daemon=True)
    t.start()


def _worker_loop() -> None:
    global _PROCESSING
    cfg = _load_config()
    max_c = int(cfg.get("max_concurrent") or 1)
    active = 0
    while True:
        if active >= max_c:
            time.sleep(0.5)
            continue
        item = None
        with _LOCK:
            if _QUEUE:
                item = heapq.heappop(_QUEUE)
                _save_state(active + 1, len(_QUEUE))
        if not item:
            time.sleep(0.25)
            continue
        _, _, doc_id, config = item
        active += 1

        def _run():
            nonlocal active
            try:
                if _RUNNER_OVERRIDE is not None:
                    _RUNNER_OVERRIDE(doc_id, config)
                else:
                    from backend.routes.generator_shared import start_video_generation
                    start_video_generation(doc_id, config)
            finally:
                active -= 1
                _save_state(active, len(_QUEUE))

        threading.Thread(target=_run, daemon=True).start()
