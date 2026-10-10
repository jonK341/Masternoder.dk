"""
Shared state and helpers for the generator (documentary + AI clips).
Used by generator_routes and optionally by missing_endpoints (e.g. debug/status).
"""
import os
import sys
import json
import threading
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _videos_dirs():
    """Yield (dir_path, is_primary). Primary = VIDEOS_DIR from env or default; then fallback subdirs under project root."""
    try:
        from backend.services.video_generator_service import VIDEOS_DIR
        if VIDEOS_DIR and os.path.isdir(VIDEOS_DIR):
            yield (VIDEOS_DIR, True)
    except Exception:
        pass
    for sub in ('vidgenerator/videos', 'output/videos', 'vidgenerator/static/videos'):
        p = os.path.join(_BASE_DIR, sub)
        if os.path.isdir(p):
            yield (p, False)


# In-memory job store for video generation (survives request lifecycle)
video_jobs = {}
video_jobs_lock = threading.Lock()


def _parse_job_timestamp(value) -> float:
    """Parse ISO updated_at for ordering; 0 if missing/invalid."""
    if not value:
        return 0.0
    try:
        raw = str(value).strip().replace('Z', '+00:00')
        return datetime.fromisoformat(raw).timestamp()
    except Exception:
        return 0.0


def _job_from_sidecar(job_id: str, sidecar: dict) -> dict:
    sc_status = str(sidecar.get('status') or '').strip().lower()
    return {
        'id': job_id,
        'job_id': job_id,
        'status': sc_status,
        'progress': int(sidecar.get('progress', 0) or 0),
        'message': sidecar.get('message') or sidecar.get('error_message') or 'Processing',
        'error_message': sidecar.get('error_message'),
        'video_url': sidecar.get('video_url')
        or (f'/api/documentary/video/{job_id}' if sc_status == 'completed' else None),
        'updated_at': sidecar.get('updated_at') or datetime.utcnow().isoformat(),
        'providers_used': sidecar.get('providers_used') or [],
        'generation_run_id': sidecar.get('generation_run_id'),
        'storyline_preview': sidecar.get('storyline_preview'),
        'visual_seed': sidecar.get('visual_seed'),
        'service_check': sidecar.get('service_check'),
        'encode_stage': sidecar.get('stage'),
    }


def _merge_sidecar_over_job(base: dict, sidecar: dict) -> dict:
    """Overlay shared sidecar fields; keep DB/memory-only fields (config, rewards)."""
    merged = dict(base)
    sc_status = str(sidecar.get('status') or '').strip().lower()
    if not sc_status:
        return merged
    sc_ts = _parse_job_timestamp(sidecar.get('updated_at'))
    base_ts = _parse_job_timestamp(merged.get('updated_at'))
    base_status = str(merged.get('status') or '').strip().lower()
    active = {'pending', 'processing'}
    prefer_sidecar = (
        base_status in active
        or sc_status in active
        or sc_ts >= base_ts
        or base_status not in ('completed', 'failed', 'error')
    )
    if not prefer_sidecar and base_status in ('completed', 'failed', 'error') and sc_ts < base_ts:
        return merged
    merged['status'] = sc_status
    merged['progress'] = int(sidecar.get('progress', merged.get('progress', 0)) or 0)
    merged['message'] = sidecar.get('message') or merged.get('message') or 'Processing'
    if sidecar.get('error_message'):
        merged['error_message'] = sidecar.get('error_message')
    if sidecar.get('video_url'):
        merged['video_url'] = sidecar.get('video_url')
    elif sc_status == 'completed':
        merged['video_url'] = merged.get('video_url') or f'/api/documentary/video/{merged.get("id") or merged.get("job_id")}'
    if sidecar.get('updated_at'):
        merged['updated_at'] = sidecar.get('updated_at')
    for key in (
        'providers_used',
        'generation_run_id',
        'storyline_preview',
        'visual_seed',
        'service_check',
        'stage',
    ):
        if sidecar.get(key) is not None:
            if key == 'stage':
                merged['encode_stage'] = sidecar.get(key)
            else:
                merged[key] = sidecar.get(key)
    return merged


def get_video_job(job_id: str):
    """Resolve job state: sidecar (cross-worker) overlays DB, then in-memory fallback."""
    sidecar = get_video_status_sidecar(job_id)
    stored = None
    try:
        from backend.services.generator_db_service import generator_tables_exist, get_job
        if generator_tables_exist():
            row = get_job(job_id)
            if row is not None:
                stored = dict(row)
    except Exception:
        pass
    if stored is None:
        with video_jobs_lock:
            mem = video_jobs.get(job_id)
            if mem is not None:
                stored = dict(mem)
    if isinstance(sidecar, dict) and sidecar.get('status'):
        if stored is None:
            return _job_from_sidecar(job_id, sidecar)
        return _merge_sidecar_over_job(stored, sidecar)
    return stored


def set_video_job(job_id: str, data: dict):
    try:
        from backend.services.generator_db_service import generator_tables_exist, save_job
        if generator_tables_exist():
            payload = dict(data)
            payload['id'] = job_id
            payload['job_id'] = job_id
            save_job(payload)
    except Exception:
        pass
    with video_jobs_lock:
        video_jobs[job_id] = data


def ensure_video_job(job_id: str, default_status: str = 'processing'):
    with video_jobs_lock:
        if job_id not in video_jobs:
            video_jobs[job_id] = {
                'id': job_id,
                'status': default_status,
                'progress': 0,
                'clips': [],
                'video_url': None,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            }
        return video_jobs[job_id]


def reset_engine_for_test():
    """Clear in-memory job store so tests start with a clean engine. Does not clear DB."""
    with video_jobs_lock:
        video_jobs.clear()


def start_documentary_encoding(doc_id: str, config: dict):
    """Start documentary encoding in subprocess (preferred) or thread."""
    try:
        from backend.services.video_generator_service import (
            _write_status_sidecar,
            write_job_config_for_subprocess,
        )
        _write_status_sidecar(
            doc_id=doc_id,
            status='processing',
            message='Starting...',
            progress=0,
            title=config.get('title'),
            prompt=config.get('prompt') or config.get('description'),
        )
        if write_job_config_for_subprocess(doc_id, config):
            import subprocess
            python = sys.executable
            cmd = [python, '-m', 'backend.run_generator_job', doc_id]
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=_BASE_DIR,
                    env=dict(os.environ, PYTHONPATH=_BASE_DIR + os.pathsep + os.environ.get('PYTHONPATH', '')),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                try:
                    from backend.services.video_generator_service import write_run_sidecar
                    write_run_sidecar(
                        doc_id,
                        proc.pid,
                        duration_sec=int(config.get('duration') or 180),
                    )
                except Exception:
                    pass
                return
            except Exception:
                pass
        start_video_generation(doc_id, config)
    except Exception:
        start_video_generation(doc_id, config)


def start_video_generation(doc_id: str, config: dict):
    """Start background video generation (thread fallback)."""
    try:
        from backend.services.video_generator_service import generate_video_background
        generate_video_background(doc_id, config, get_video_job, set_video_job)
    except Exception as e:
        print(f"[VideoGenerator] Background start failed: {e}")


def start_ai_clips_generation(job_id: str, config: dict):
    """Start background AI clips generation."""
    try:
        from backend.services.video_generator_service import generate_ai_clips_background
        generate_ai_clips_background(job_id, config, get_video_job, set_video_job)
    except Exception as e:
        print(f"[VideoGenerator] AI clips background start failed: {e}")


def get_video_file_path(doc_id: str):
    """Find video file path for doc_id. Checks VIDEOS_DIR first, then project subdirs."""
    for dir_path, _ in _videos_dirs():
        p = os.path.join(dir_path, f'{doc_id}.mp4')
        if os.path.isfile(p):
            try:
                if os.path.getsize(p) < 1024:
                    continue
            except Exception:
                continue
            return p
    return None


def get_video_status_sidecar(doc_id: str):
    """Read shared status sidecar for cross-worker progress. Checks VIDEOS_DIR first."""
    for dir_path, _ in _videos_dirs():
        p = os.path.join(dir_path, f'{doc_id}.status.json')
        if os.path.isfile(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
    return None
