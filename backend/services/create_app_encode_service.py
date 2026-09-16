"""Create App encode execution — podcast audio jobs + generator video jobs from Super Encoder package."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CREATE_APP_CHANNEL = "masternoder-main"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audio_profile(app: Dict[str, Any]) -> str:
    pkg = app.get("super_encoder") or {}
    return str(pkg.get("audio_profile") or "ultra")


def _video_profile(app: Dict[str, Any]) -> str:
    pkg = app.get("super_encoder") or {}
    return str(pkg.get("video_profile") or "premium")


def _quality_goal(app: Dict[str, Any]) -> str:
    return str(app.get("quality_goal") or "balanced")


def _content_hint(app: Dict[str, Any]) -> str:
    return str(app.get("content_hint") or app.get("title") or "Create App product")


def _duration_sec(app: Dict[str, Any]) -> int:
    return max(10, min(300, int(app.get("duration_sec") or 120)))


def start_podcast_encode_job(
    user_id: str,
    app: Dict[str, Any],
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Queue podcast TTS + audio encode using super_encoder.audio_profile."""
    targets = app.get("targets") or {}
    if not targets.get("podcast"):
        return {"success": False, "skipped": True, "reason": "podcast_not_targeted"}

    existing = ((app.get("encode_jobs") or {}).get("podcast")) or {}
    if existing.get("job_id") and not force and existing.get("status") not in ("failed", None):
        return {"success": True, "skipped": True, "reason": "already_started", **existing}

    from backend.services.podcast_service import start_generate_job

    title = str(app.get("title") or "Create App Podcast")
    hint = _content_hint(app)
    profile = _audio_profile(app)
    result = start_generate_job(
        user_id,
        topic=hint,
        title=title,
        description=f"Create App {app.get('id')} — Super Encoder ({profile})",
        channel_id=_CREATE_APP_CHANNEL,
        encode_profile=profile,
        assigned_agent="podcast_producer_agent",
    )
    if not result.get("success"):
        return result

    return {
        "success": True,
        "job_id": result.get("job_id"),
        "status": result.get("status") or "queued",
        "encode_profile": profile,
        "channel_id": _CREATE_APP_CHANNEL,
        "create_app_id": app.get("id"),
        "started_at": _now_iso(),
    }


def start_video_encode_job(
    user_id: str,
    app: Dict[str, Any],
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Start generator documentary encode using super_encoder.video_profile."""
    targets = app.get("targets") or {}
    if not targets.get("playstore"):
        return {"success": False, "skipped": True, "reason": "playstore_not_targeted"}

    existing = ((app.get("encode_jobs") or {}).get("video")) or {}
    doc_id = existing.get("documentary_id")
    if doc_id and not force and existing.get("status") not in ("failed", None):
        return {"success": True, "skipped": True, "reason": "already_started", **existing}

    doc_id = str(uuid.uuid4())
    profile = _video_profile(app)
    hint = _content_hint(app)
    title = str(app.get("title") or "Create App Video")
    config: Dict[str, Any] = {
        "prompt": hint,
        "title": title,
        "description": hint,
        "user_id": user_id,
        "duration": _duration_sec(app),
        "encode_profile": profile,
        "quality_mode": _quality_goal(app),
        "create_app_id": app.get("id"),
        "audio_enabled": True,
        "source": "create_app",
    }

    from backend.routes.generator_shared import ensure_video_job, set_video_job

    ensure_video_job(doc_id, "processing")
    job = {
        "id": doc_id,
        "status": "processing",
        "progress": 0,
        "type": "documentary",
        "config": config,
        "create_app_id": app.get("id"),
        "video_url": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    set_video_job(doc_id, job)

    started = False
    start_error: Optional[str] = None
    try:
        from backend.routes.generator_shared import start_documentary_encoding

        start_documentary_encoding(doc_id, config)
        started = True
    except Exception as exc:
        start_error = str(exc)[:200]
        try:
            from backend.routes.generator_shared import start_video_generation

            start_video_generation(doc_id, config)
            started = True
        except Exception as exc2:
            start_error = str(exc2)[:200]

    if not started:
        return {"success": False, "error": start_error or "video_encode_start_failed"}

    return {
        "success": True,
        "documentary_id": doc_id,
        "status": "processing",
        "encode_profile": profile,
        "create_app_id": app.get("id"),
        "started_at": _now_iso(),
    }


def refresh_podcast_job_status(podcast_job: Dict[str, Any]) -> Dict[str, Any]:
    """Merge latest podcast job progress into stored encode_jobs.podcast record."""
    job_id = podcast_job.get("job_id")
    if not job_id:
        return podcast_job

    from backend.services.podcast_service import get_job_progress

    prog = get_job_progress(job_id)
    if not prog.get("success"):
        return {**podcast_job, "status": "unknown", "poll_error": prog.get("error")}

    out = {**podcast_job}
    out["status"] = prog.get("status") or out.get("status")
    out["progress"] = prog.get("progress")
    if prog.get("episode_id"):
        out["episode_id"] = prog.get("episode_id")
    if prog.get("audio_url"):
        out["audio_url"] = prog.get("audio_url")
    if prog.get("error"):
        out["error"] = prog.get("error")
    out["updated_at"] = _now_iso()
    return out


def _read_video_sidecar(doc_id: str) -> Dict[str, Any]:
    try:
        from backend.services.video_generator_service import VIDEOS_DIR

        path = os.path.join(VIDEOS_DIR, f"{doc_id}.status.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def refresh_video_job_status(video_job: Dict[str, Any]) -> Dict[str, Any]:
    """Merge generator job store + sidecar into encode_jobs.video record."""
    doc_id = video_job.get("documentary_id")
    if not doc_id:
        return video_job

    out = {**video_job}
    try:
        from backend.routes.generator_shared import get_video_job

        row = get_video_job(doc_id) or {}
        if row.get("status"):
            out["status"] = row.get("status")
        if row.get("progress") is not None:
            out["progress"] = row.get("progress")
        if row.get("video_url"):
            out["video_url"] = row.get("video_url")
        if row.get("error_message") or row.get("error"):
            out["error"] = row.get("error_message") or row.get("error")
    except Exception:
        pass

    sidecar = _read_video_sidecar(doc_id)
    if sidecar.get("status"):
        out["status"] = sidecar.get("status")
    if sidecar.get("progress") is not None:
        out["progress"] = sidecar.get("progress")
    if sidecar.get("video_url"):
        out["video_url"] = sidecar.get("video_url")
    if sidecar.get("error_message"):
        out["error"] = sidecar.get("error_message")
    out["updated_at"] = _now_iso()
    return out


def refresh_encode_jobs(encode_jobs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    jobs = dict(encode_jobs or {})
    if jobs.get("podcast"):
        jobs["podcast"] = refresh_podcast_job_status(jobs["podcast"])
    if jobs.get("video"):
        jobs["video"] = refresh_video_job_status(jobs["video"])
    return jobs


def start_encode_jobs_for_app(
    user_id: str,
    app: Dict[str, Any],
    *,
    force: bool = False,
) -> Dict[str, Any]:
    """Start podcast and/or video encode jobs based on app targets and Super Encoder package."""
    jobs: Dict[str, Any] = dict(app.get("encode_jobs") or {})
    started: Dict[str, Any] = {}

    podcast_res = start_podcast_encode_job(user_id, app, force=force)
    if podcast_res.get("success") and not podcast_res.get("skipped"):
        jobs["podcast"] = podcast_res
        started["podcast"] = podcast_res
    elif jobs.get("podcast"):
        started["podcast"] = podcast_res

    video_res = start_video_encode_job(user_id, app, force=force)
    if video_res.get("success") and not video_res.get("skipped"):
        jobs["video"] = video_res
        started["video"] = video_res
    elif jobs.get("video"):
        started["video"] = video_res

    jobs = refresh_encode_jobs(jobs)
    return {"success": True, "encode_jobs": jobs, "started": started}


def encode_jobs_summary(encode_jobs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    jobs = refresh_encode_jobs(encode_jobs)
    podcast = jobs.get("podcast") or {}
    video = jobs.get("video") or {}
    statuses = [s for s in (podcast.get("status"), video.get("status")) if s]
    all_done = bool(statuses) and all(s in ("completed",) for s in statuses)
    any_failed = any(s == "failed" for s in statuses)
    any_running = any(
        s in ("queued", "scripting", "tts", "encoding", "processing", "pending")
        for s in statuses
    )
    return {
        "encode_jobs": jobs,
        "all_completed": all_done,
        "any_failed": any_failed,
        "any_running": any_running,
    }
