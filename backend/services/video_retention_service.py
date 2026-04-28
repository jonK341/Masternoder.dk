"""
Video retention: temp storage with 5 min download window; keep only top 10 by file size (best quality).
Cleanup deletes any video older than TEMP_EXPIRY_MINUTES that is not in the top 10.
"""
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEOS_DIR = os.environ.get("VIDEOS_DIR") or os.path.join(_BASE, "vidgenerator", "videos")

TOP_N = 10
TEMP_EXPIRY_MINUTES = 5
_MIN_VALID_MP4_BYTES = 1024


def _status_path(doc_id: str) -> str:
    return os.path.join(VIDEOS_DIR, f"{doc_id}.status.json")


def _mp4_path(doc_id: str) -> str:
    return os.path.join(VIDEOS_DIR, f"{doc_id}.mp4")


def _read_status(doc_id: str) -> Optional[Dict[str, Any]]:
    p = _status_path(doc_id)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_all_mp4_with_size() -> List[Tuple[str, int]]:
    """Return list of (doc_id, size_bytes) for all valid mp4 in VIDEOS_DIR, sorted by size desc."""
    if not os.path.isdir(VIDEOS_DIR):
        return []
    out = []
    for f in os.listdir(VIDEOS_DIR):
        if not f.endswith(".mp4"):
            continue
        base = os.path.splitext(f)[0]
        path = os.path.join(VIDEOS_DIR, f)
        try:
            if os.path.isfile(path) and os.path.getsize(path) >= _MIN_VALID_MP4_BYTES:
                out.append((base, os.path.getsize(path)))
        except Exception:
            continue
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def get_top_n_ids(n: int = TOP_N) -> List[str]:
    """Return doc_ids of the top N videos by file size (best quality)."""
    pairs = get_all_mp4_with_size()
    return [doc_id for doc_id, _ in pairs[:n]]


def get_recent_temp_videos() -> List[Dict[str, Any]]:
    """
    Return list of recent completed videos that are still within the 5 min window.
    Each item: id, title, video_url, download_url, expires_at_iso, seconds_left.
    """
    pairs = get_all_mp4_with_size()
    top_ids = set(get_top_n_ids(TOP_N))
    now = datetime.utcnow()
    expiry_delta = timedelta(minutes=TEMP_EXPIRY_MINUTES)
    out = []
    for doc_id, size in pairs:
        st = _read_status(doc_id)
        if not st or st.get("status") != "completed":
            continue
        updated = st.get("updated_at")
        if not updated:
            continue
        try:
            raw = updated.replace("Z", "").strip()
            updated_dt = datetime.fromisoformat(raw)
            if updated_dt.tzinfo:
                updated_dt = updated_dt.replace(tzinfo=None)
            expires_at = updated_dt + expiry_delta
        except Exception:
            continue
        if now >= expires_at:
            continue
        secs = max(0, int((expires_at - now).total_seconds()))
        video_url = st.get("video_url") or f"/vidgenerator/api/documentary/video/{doc_id}"
        download_url = video_url + "?download=1"
        out.append({
            "id": doc_id,
            "title": (st.get("title") or doc_id)[:120],
            "video_url": video_url,
            "download_url": download_url,
            "expires_at": expires_at.isoformat() + "Z",
            "seconds_left": secs,
        })
    # Sort by expires_at ascending (soonest first)
    out.sort(key=lambda x: x["expires_at"])
    return out


def run_cleanup() -> Tuple[int, List[str]]:
    """
    Delete videos that are (1) older than TEMP_EXPIRY_MINUTES and (2) not in top TOP_N by size.
    Returns (deleted_count, list of deleted doc_ids).
    """
    top_ids = set(get_top_n_ids(TOP_N))
    pairs = get_all_mp4_with_size()
    now = datetime.utcnow()
    expiry_delta = timedelta(minutes=TEMP_EXPIRY_MINUTES)
    deleted = []
    for doc_id, _ in pairs:
        if doc_id in top_ids:
            continue
        st = _read_status(doc_id)
        updated = (st or {}).get("updated_at") if st else None
        if not updated:
            # No status: use file mtime
            path = _mp4_path(doc_id)
            if os.path.isfile(path):
                try:
                    mtime = os.path.getmtime(path)
                    updated_dt = datetime.utcfromtimestamp(mtime)
                except Exception:
                    updated_dt = now
            else:
                continue
        else:
            try:
                raw = updated.replace("Z", "").strip()
                updated_dt = datetime.fromisoformat(raw)
                if updated_dt.tzinfo:
                    updated_dt = updated_dt.replace(tzinfo=None)
            except Exception:
                continue
        expires_at = updated_dt + expiry_delta
        if now < expires_at:
            continue
        path = _mp4_path(doc_id)
        if os.path.isfile(path):
            try:
                os.remove(path)
                deleted.append(doc_id)
            except Exception:
                pass
        status_path = _status_path(doc_id)
        if os.path.isfile(status_path):
            try:
                os.remove(status_path)
            except Exception:
                pass
    return (len(deleted), deleted)


def clear_all_video_storage(include_fallback_dirs: bool = True) -> Tuple[int, List[str]]:
    """
    Delete all video files and related metadata from VIDEOS_DIR (and optionally fallback dirs).
    Use to empty the gallery and free all video storage.
    Returns (deleted_count, list of deleted file paths).
    """
    deleted = []
    # Primary dir: all .mp4, .webm, .status.json, .pipeline.json, .job.json, *_temp_audio.mp4
    if os.path.isdir(VIDEOS_DIR):
        for f in os.listdir(VIDEOS_DIR):
            if f.endswith((".mp4", ".webm", ".mkv")) or f.endswith((".status.json", ".pipeline.json", ".job.json")):
                path = os.path.join(VIDEOS_DIR, f)
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                        deleted.append(path)
                    except Exception:
                        pass
    if not include_fallback_dirs:
        return (len(deleted), deleted)
    # Fallback dirs (same structure: mp4 at root)
    fallback_roots = [
        os.path.join(_BASE, "vidgenerator", "static", "videos"),
        os.path.join(_BASE, "output", "videos"),
        os.path.join(_BASE, "static", "videos"),
        os.path.join(_BASE, "videos"),
    ]
    for root in fallback_roots:
        if not os.path.isdir(root):
            continue
        for f in os.listdir(root):
            if f.endswith((".mp4", ".webm", ".mkv")):
                path = os.path.join(root, f)
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                        deleted.append(path)
                    except Exception:
                        pass
    return (len(deleted), deleted)
