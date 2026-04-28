"""
Gallery Routes
API endpoints for gallery list, video details, and download.
Pipeline: generator creates video -> writes to vidgenerator/videos/{doc_id}.mp4 -> gallery lists all
valid MP4s in VIDEOS_DIR (after retention cleanup removes expired non-top files).
"""
from flask import Blueprint, jsonify, request, send_file
import os
import json
import time

gallery_bp = Blueprint("gallery", __name__)

# In-memory cache for gallery list (reduces disk/DB hits)
_gallery_list_cache = None
_gallery_list_cache_ts = 0
GALLERY_CACHE_TTL_SEC = int(os.environ.get("GALLERY_CACHE_TTL_SEC", "30"))

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Primary dir for generated videos; gallery lists every valid MP4 here (sorted by size desc in retention helpers)
VIDEOS_DIR = os.environ.get("VIDEOS_DIR") or os.path.join(_BASE, "vidgenerator", "videos")
# Fallback dirs for download lookup only (gallery list is top 10 from VIDEOS_DIR only)
VIDEO_SUBDIRS = ("vidgenerator/static/videos", "vidgenerator/videos", "output/videos", "static/videos", "videos")


def _gallery_admin_token_configured() -> bool:
    return bool(os.environ.get("GALLERY_ADMIN_TOKEN", "").strip())


def _check_gallery_admin_token():
    """Validate X-Gallery-Admin-Token against GALLERY_ADMIN_TOKEN. Returns (ok, error_message)."""
    expected = os.environ.get("GALLERY_ADMIN_TOKEN", "").strip()
    if not expected:
        return False, "Gallery admin is not configured (set GALLERY_ADMIN_TOKEN in the server environment)"
    got = (request.headers.get("X-Gallery-Admin-Token") or "").strip()
    if not got:
        return False, "Missing X-Gallery-Admin-Token header"
    if got != expected:
        return False, "Invalid admin token"
    return True, None


def _read_video_metadata(video_dir: str, base: str) -> dict:
    """Read title/description from pipeline.json or status.json when available."""
    meta = {}
    for ext in (".pipeline.json", ".status.json"):
        p = os.path.join(video_dir, base + ext)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    meta["title"] = meta.get("title") or data.get("title")
                    meta["description"] = meta.get("description") or data.get("description") or data.get("prompt")
                    meta["prompt"] = meta.get("prompt") or data.get("prompt")
            except Exception:
                pass
    return meta


def _list_videos_cached():
    """Return gallery list, using cache when fresh."""
    global _gallery_list_cache, _gallery_list_cache_ts
    now = time.time()
    if _gallery_list_cache is not None and (now - _gallery_list_cache_ts) < GALLERY_CACHE_TTL_SEC:
        return _gallery_list_cache
    _gallery_list_cache = _list_videos()
    _gallery_list_cache_ts = now
    return _gallery_list_cache


def _list_videos():
    """List all valid MP4s in VIDEOS_DIR (newest / largest first). Runs retention cleanup first."""
    try:
        from backend.services.video_retention_service import get_all_mp4_with_size, run_cleanup
        run_cleanup()
        pairs = get_all_mp4_with_size()
    except Exception:
        pairs = []
    out = []
    max_size = max((s for _, s in pairs), default=1)
    if os.path.isdir(VIDEOS_DIR):
        for base, size in pairs:
            path = os.path.join(VIDEOS_DIR, base + ".mp4")
            if not os.path.isfile(path) or os.path.getsize(path) < 1024:
                continue
            meta = _read_video_metadata(VIDEOS_DIR, base)
            title = (meta.get("title") or "").strip() or base.replace("-", " ").replace("_", " ").title()
            desc = (meta.get("description") or meta.get("prompt") or "").strip()
            # Size-based score so sort-by-quality and filters behave sensibly
            qscore = min(1.0, max(0.0, float(size) / float(max_size))) if max_size else 0.5
            qlevel = "high" if qscore >= 0.85 else "medium" if qscore >= 0.45 else "low"
            out.append({
                "id": base,
                "title": title[:120],
                "status": "completed",
                "thumbnail_path": "",
                "duration": 0,
                "created_at": _mtime(path),
                "quality_level": qlevel,
                "quality_score": round(qscore, 4),
                "category_name": "Documentary",
                "description": desc[:500],
                "prompt": desc[:500],
                "video_url": f"/api/documentary/video/{base}",
            })
    # Sample entries when no files found (extra test data for context)
    if not out:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        for i, t in enumerate([
            ("Welcome to MasterNoder", "Documentary", "Introduction to the platform."),
            ("Galaxy Hunters", "Documentary", "Star map and trophy hunters."),
            ("Electric Magnet Tech", "Documentary", "Verification and DNA specials."),
        ]):
            out.append({
                "id": f"sample-{i+1}",
                "title": t[0],
                "status": "completed",
                "thumbnail_path": "",
                "duration": 60 + i * 30,
                "created_at": (now - timedelta(days=i)).isoformat() + "Z",
                "quality_level": "medium",
                "quality_score": 0.7 + i * 0.1,
                "category_name": t[1],
                "description": t[2],
                "prompt": t[2],
            })
    return out


def _mtime(path):
    try:
        from datetime import datetime
        return datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat() + "Z"
    except Exception:
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


@gallery_bp.route("/api/categories/list", methods=["GET"])
def categories_list():
    """List categories for gallery filter."""
    try:
        cats = [
            {"name": "Documentary"},
            {"name": "Tutorial"},
            {"name": "Gallery"},
            {"name": "Tech"},
            {"name": "Game"},
        ]
        return jsonify({"success": True, "categories": cats}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "categories": []}), 500


@gallery_bp.route("/api/gallery/recent-temp", methods=["GET"])
def gallery_recent_temp():
    """List recent completed videos still within 5 min download window (for profile countdown). Runs cleanup."""
    try:
        from backend.services.video_retention_service import get_recent_temp_videos, run_cleanup
        run_cleanup()
        videos = get_recent_temp_videos()
        return jsonify({"success": True, "videos": videos, "expires_minutes": 5}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "videos": []}), 500


@gallery_bp.route("/api/gallery/downloads", methods=["GET"])
def gallery_my_downloads():
    """List current user's downloads (when DB migration run)."""
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"status": "success", "downloads": []}), 200
        from backend.services.gallery_db_service import gallery_tables_exist, get_user_downloads
        if not gallery_tables_exist():
            return jsonify({"status": "success", "downloads": []}), 200
        downloads = get_user_downloads(user_id) or []
        return jsonify({"status": "success", "downloads": downloads}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "downloads": []}), 500


@gallery_bp.route("/api/gallery/list", methods=["GET"])
def gallery_list():
    """List videos with optional search, status, category, quality, sort."""
    try:
        search = (request.args.get("search") or "").strip().lower()
        status = request.args.get("status", "all")
        category = (request.args.get("category") or "").strip().lower()
        quality = (request.args.get("quality") or "").strip().lower()
        sort = request.args.get("sort", "newest")
        limit = max(1, min(500, int(request.args.get("limit", 100))))
        offset = max(0, int(request.args.get("offset", 0)))

        videos = _list_videos_cached()

        if search:
            videos = [v for v in videos if search in (v.get("title") or "").lower()
                      or search in (v.get("description") or "").lower()
                      or search in (v.get("prompt") or "").lower()
                      or search in str(v.get("id") or "").lower()]
        if status and status != "all":
            videos = [v for v in videos if (v.get("status") or "").lower() == status.lower()]
        if category:
            videos = [v for v in videos if category in (v.get("category_name") or "").lower()]
        if quality:
            videos = [v for v in videos if quality in (v.get("quality_level") or "").lower()]

        if sort == "newest":
            videos = sorted(videos, key=lambda v: v.get("created_at") or "", reverse=True)
        elif sort == "oldest":
            videos = sorted(videos, key=lambda v: v.get("created_at") or "")
        elif sort == "title":
            videos = sorted(videos, key=lambda v: (v.get("title") or "").lower())
        elif sort == "duration":
            videos = sorted(videos, key=lambda v: float(v.get("duration") or 0), reverse=True)
        elif sort == "quality":
            videos = sorted(videos, key=lambda v: (v.get("quality_level") or "").lower())
        elif sort == "quality_score":
            videos = sorted(videos, key=lambda v: float(v.get("quality_score") or 0), reverse=True)

        total = len(videos)
        videos = videos[offset: offset + limit]

        return jsonify({
            "status": "success",
            "videos": videos,
            "count": len(videos),
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(videos)) < total,
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e), "videos": []}), 500


@gallery_bp.route("/api/gallery/video/<video_id>", methods=["GET"])
def gallery_video(video_id):
    """Get single video details. Records view when DB and user_id available."""
    try:
        user_id = request.args.get("user_id")
        if user_id:
            try:
                from backend.services.gallery_db_service import gallery_tables_exist, record_view
                if gallery_tables_exist():
                    record_view(user_id, str(video_id))
            except Exception:
                pass
        videos = _list_videos()
        for v in videos:
            if str(v.get("id")) == str(video_id):
                return jsonify({"status": "success", "video": v}), 200
        return jsonify({"status": "error", "error": "Video not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gallery_bp.route("/api/gallery/video/<video_id>/ai-description", methods=["GET"])
def gallery_ai_description(video_id):
    """
    Generate or retrieve an AI-enhanced title, description, and tags for a gallery video.
    Uses Groq (fast) so it's near-instant.

    GET ?user_id=X&regenerate=true
    """
    try:
        videos = _list_videos()
        video = next((v for v in videos if str(v.get("id")) == str(video_id)), None)
        if not video:
            return jsonify({"success": False, "error": "Video not found"}), 404

        current_title = video.get("title") or video_id
        current_desc  = video.get("description") or video.get("prompt") or ""

        from backend.services.llm_service import chat
        resp = chat(
            messages=[{
                "role": "user",
                "content": (
                    f"You are a creative copywriter for an AI video platform. "
                    f"Given this video info, generate an enhanced title, a compelling 2-sentence description, "
                    f"and 5 relevant tags. Return ONLY valid JSON.\n\n"
                    f"Current title: {current_title}\n"
                    f"Current description: {current_desc[:500]}\n\n"
                    f"Return: {{\"title\": \"...\", \"description\": \"...\", \"tags\": [\"...\", ...]}}"
                ),
            }],
            task_type="speed",
            max_tokens=300,
            temperature=0.8,
        )

        if not resp.success:
            return jsonify({"success": False, "error": resp.error}), 200

        raw = resp.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            enhanced = json.loads(raw)
        except Exception:
            enhanced = {"title": current_title, "description": current_desc, "tags": []}

        return jsonify({
            "success": True,
            "video_id": video_id,
            "enhanced": enhanced,
            "provider": resp.provider,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@gallery_bp.route("/api/gallery/admin/status", methods=["GET"])
def gallery_admin_status():
    """Whether bulk LLM metadata tools are available (token configured on server)."""
    return jsonify({
        "enhance_metadata_configured": _gallery_admin_token_configured(),
    }), 200


@gallery_bp.route("/api/gallery/enhance-metadata", methods=["POST"])
def gallery_enhance_metadata():
    """
    Bulk-enhance metadata for all gallery videos with weak descriptions.
    Requires header X-Gallery-Admin-Token matching env GALLERY_ADMIN_TOKEN.
    Body: {"max_videos": 10}
    Returns list of enhanced results.
    """
    try:
        ok, err = _check_gallery_admin_token()
        if not ok:
            return jsonify({"success": False, "error": err}), 403

        data = request.get_json(silent=True) or {}
        max_videos = min(int(data.get("max_videos", 5)), 20)

        videos = _list_videos()
        # Target videos with weak or auto-generated descriptions
        weak = [v for v in videos if len((v.get("description") or "").strip()) < 40][:max_videos]

        if not weak:
            return jsonify({"success": True, "enhanced": 0, "message": "All videos already have good descriptions"}), 200

        from backend.services.llm_service import chat
        results = []
        for v in weak:
            title   = v.get("title") or v.get("id") or "Untitled"
            current = v.get("description") or v.get("prompt") or ""
            resp = chat(
                messages=[{
                    "role": "user",
                    "content": (
                        f"Generate an enhanced title and 2-sentence description for an AI video titled '{title}'. "
                        f"Context: {current[:300]}. "
                        "Return ONLY JSON: {\"title\": \"...\", \"description\": \"...\", \"tags\": [...]}"
                    ),
                }],
                task_type="speed",
                max_tokens=250,
                temperature=0.75,
            )
            if resp.success:
                raw = resp.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                try:
                    enhanced = json.loads(raw)
                except Exception:
                    enhanced = {"title": title, "description": current}
                results.append({"video_id": v.get("id"), "enhanced": enhanced})

        return jsonify({
            "success": True,
            "enhanced": len(results),
            "results": results,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@gallery_bp.route("/api/gallery/clean", methods=["POST"])
def gallery_clean():
    """
    Clean the gallery directory: run retention cleanup (remove expired, keep top 10).
    Body: {"full": true} to clear all video storage (use with care).
    Returns deleted_count and deleted_ids.
    """
    global _gallery_list_cache, _gallery_list_cache_ts
    try:
        data = request.get_json(silent=True) or {}
        full = bool(data.get("full", False))
        if full:
            from backend.services.video_retention_service import clear_all_video_storage
            deleted_count, deleted_paths = clear_all_video_storage(include_fallback_dirs=True)
            _gallery_list_cache = None
            _gallery_list_cache_ts = 0
            return jsonify({
                "status": "success",
                "cleaned": True,
                "full_clean": True,
                "deleted_count": deleted_count,
                "deleted": [str(p) for p in deleted_paths[:50]],
            }), 200
        from backend.services.video_retention_service import run_cleanup
        deleted_count, deleted_ids = run_cleanup()
        _gallery_list_cache = None
        _gallery_list_cache_ts = 0
        return jsonify({
            "status": "success",
            "cleaned": True,
            "deleted_count": deleted_count,
            "deleted_ids": deleted_ids,
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gallery_bp.route("/api/gallery/video/<video_id>/download", methods=["GET"])
def gallery_download(video_id):
    """Download video file if it exists. Records download when DB and user_id available."""
    try:
        user_id = request.args.get("user_id")
        if user_id:
            try:
                from backend.services.gallery_db_service import gallery_tables_exist, record_download
                if gallery_tables_exist():
                    record_download(user_id, str(video_id))
            except Exception:
                pass
        for sub in ("vidgenerator/static/videos", "vidgenerator/videos", "output/videos", "static/videos", "videos"):
            d = os.path.join(_BASE, sub)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                base = os.path.splitext(f)[0]
                if base == video_id and f.endswith((".mp4", ".webm", ".mkv")):
                    path = os.path.join(d, f)
                    return send_file(path, as_attachment=True, download_name=f)
        return jsonify({"status": "error", "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gallery_bp.route("/api/gallery/quality-gate", methods=["POST"])
def gallery_quality_gate():
    """
    Quality gate before promoting copy or listing highlights — uses agent_output_evaluator
    (LLM judge when keys exist, else heuristic). Body: { video_id?, text?, title?, strict? }.
    """
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or data.get("content") or "").strip()
        title = (data.get("title") or "").strip()
        video_id = data.get("video_id")
        if video_id and not text:
            videos = _list_videos()
            v = next((x for x in videos if str(x.get("id")) == str(video_id)), None)
            if not v:
                return jsonify({"status": "error", "error": "Video not found"}), 404
            text = (v.get("description") or v.get("prompt") or v.get("title") or "") or ""
            title = title or (v.get("title") or "")
        if not text:
            return jsonify({"status": "error", "error": "text or video_id required"}), 400

        from backend.services.agent_output_evaluator import evaluate_content

        ev = evaluate_content(
            text,
            content_type="gallery_video",
            title=title,
            strict=bool(data.get("strict", False)),
        )
        return jsonify({"status": "success", "evaluation": ev}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
