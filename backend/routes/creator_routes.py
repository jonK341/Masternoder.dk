"""Creator Super Encoder routes — music, songs, video, MN2 ratings, mobile config."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request, send_file, abort

creator_bp = Blueprint("creator", __name__)


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        body = request.get_json(silent=True) or {}
        return request.args.get("user_id") or body.get("user_id") or "default_user"


@creator_bp.route("/api/creator/config", methods=["GET"])
def creator_config():
    from backend.services.super_encoder_service import get_config, get_storage_stats, get_ai_status, list_encoder_modes
    cfg = get_config()
    return jsonify({
        "success": True,
        "config": {
            "app_name": cfg.get("app_name"),
            "app_tagline": cfg.get("app_tagline"),
            "max_videos": cfg.get("max_videos"),
            "landing_url": cfg.get("landing_url"),
            "encode": cfg.get("encode"),
            "rating": cfg.get("rating"),
            "default_encoder_mode": cfg.get("default_encoder_mode"),
        },
        "encoder_modes": list_encoder_modes(),
        "storage": get_storage_stats(),
        "ai": get_ai_status(),
    }), 200


@creator_bp.route("/api/creator/modes", methods=["GET"])
def creator_encoder_modes():
    from backend.services.super_encoder_service import list_encoder_modes
    return jsonify(list_encoder_modes()), 200


@creator_bp.route("/api/creator/mobile/config", methods=["GET"])
def creator_mobile_config():
    from backend.services.super_encoder_service import get_mobile_config
    return jsonify(get_mobile_config()), 200


@creator_bp.route("/api/creator/encode", methods=["POST"])
def creator_encode():
    """One-click Super Encode — music + song + video with sync."""
    body = request.get_json(silent=True) or {}
    uid = _resolve_uid()
    title = (body.get("title") or "").strip()
    if not title:
        return jsonify({"success": False, "error": "title required"}), 400
    from backend.services.super_encoder_service import one_click_encode
    result = one_click_encode(
        user_id=uid,
        title=title,
        genre=(body.get("genre") or "electronic").strip(),
        mood=(body.get("mood") or "energetic").strip(),
        duration=int(body.get("duration") or 60),
        pay_with_mn2=bool(body.get("pay_with_mn2", True)),
        mode_id=(body.get("mode") or body.get("encoder_mode") or "").strip() or None,
    )
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@creator_bp.route("/api/creator/tracks", methods=["GET"])
def creator_list_tracks():
    from backend.services.super_encoder_service import list_tracks
    uid = request.args.get("user_id")
    mine = request.args.get("mine") == "1"
    limit = min(125, int(request.args.get("limit") or 50))
    return jsonify(list_tracks(user_id=uid if mine else None, limit=limit)), 200


@creator_bp.route("/api/creator/tracks/<track_id>", methods=["GET"])
def creator_get_track(track_id):
    from backend.services.super_encoder_service import get_track, get_storage_stats
    track = get_track(track_id)
    if not track:
        return jsonify({"success": False, "error": "Track not found"}), 404
    from backend.services.creator_rating_service import get_track_ratings
    ratings = get_track_ratings(track_id)
    return jsonify({"success": True, "track": track, "ratings": ratings, "storage": get_storage_stats()}), 200


@creator_bp.route("/api/creator/tracks/<track_id>/audio", methods=["GET"])
def creator_track_audio(track_id):
    from backend.services.super_encoder_service import _storage_dir
    path = os.path.join(_storage_dir(), f"{track_id}_audio.mp3")
    if not os.path.isfile(path):
        abort(404)
    return send_file(path, mimetype="audio/mpeg", conditional=True)


@creator_bp.route("/api/creator/tracks/<track_id>/sync", methods=["GET"])
def creator_track_sync(track_id):
    from backend.services.super_encoder_service import _storage_dir, get_track
    path = os.path.join(_storage_dir(), f"{track_id}_sync.mp4")
    if not os.path.isfile(path):
        track = get_track(track_id)
        if track and track.get("doc_id"):
            from backend.services.video_generator_service import VIDEOS_DIR
            fallback = os.path.join(VIDEOS_DIR, f"{track['doc_id']}.mp4")
            if os.path.isfile(fallback):
                return send_file(fallback, mimetype="video/mp4", conditional=True)
        abort(404)
    return send_file(path, mimetype="video/mp4", conditional=True)


@creator_bp.route("/api/creator/tracks/<track_id>/video", methods=["GET"])
def creator_track_video(track_id):
    from backend.services.super_encoder_service import get_track
    track = get_track(track_id)
    if not track or not track.get("doc_id"):
        abort(404)
    from backend.services.video_generator_service import VIDEOS_DIR
    path = os.path.join(VIDEOS_DIR, f"{track['doc_id']}.mp4")
    if not os.path.isfile(path):
        abort(404)
    return send_file(path, mimetype="video/mp4", conditional=True)


@creator_bp.route("/api/creator/rate", methods=["POST"])
def creator_rate():
    """Rate a track with MN2 crypto payment."""
    body = request.get_json(silent=True) or {}
    uid = _resolve_uid()
    track_id = (body.get("track_id") or "").strip()
    score = body.get("score")
    if not track_id or score is None:
        return jsonify({"success": False, "error": "track_id and score required"}), 400
    from backend.services.creator_rating_service import rate_track
    result = rate_track(uid, track_id, int(score), pay_with_mn2=bool(body.get("pay_with_mn2", True)))
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@creator_bp.route("/api/creator/rating/config", methods=["GET"])
def creator_rating_config():
    from backend.services.creator_rating_service import get_rating_config
    return jsonify(get_rating_config()), 200


@creator_bp.route("/api/creator/feed", methods=["GET"])
def creator_feed():
    """Featured rated content feed."""
    from backend.services.creator_rating_service import get_featured_tracks
    limit = min(50, int(request.args.get("limit") or 20))
    return jsonify(get_featured_tracks(limit=limit)), 200


@creator_bp.route("/api/creator/storage", methods=["GET"])
def creator_storage():
    from backend.services.super_encoder_service import get_storage_stats
    return jsonify(get_storage_stats()), 200


@creator_bp.route("/api/creator/music/status", methods=["GET"])
def creator_music_status():
    from backend.services.music_api_service import get_music_provider_status
    return jsonify(get_music_provider_status()), 200


@creator_bp.route("/api/creator/download", methods=["GET"])
def creator_download_apk():
    """Redirect to self-hosted release APK on masternoder.dk."""
    from flask import redirect
    from backend.services.super_encoder_service import get_mobile_config
    cfg = get_mobile_config()
    url = cfg.get("download_apk_url") or "/static/downloads/masternoder-creator.apk"
    return redirect(url, code=302)
