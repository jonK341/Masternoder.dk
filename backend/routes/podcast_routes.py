"""Podcast routes — channels, episodes, crypto rewards, AI generator, agents."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

podcast_bp = Blueprint("podcast", __name__)


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get("user_id") or (request.get_json(silent=True) or {}).get("user_id") or "default_user"


@podcast_bp.route("/api/podcast/channels", methods=["GET"])
def podcast_channels():
    from backend.services.podcast_service import get_channels
    return jsonify({"success": True, "channels": get_channels()}), 200


@podcast_bp.route("/api/podcast/episodes", methods=["GET"])
def podcast_episodes():
    from backend.services.podcast_service import get_episodes, annotate_episode_access
    from backend.services.podcast_social_service import get_episode_like_count, get_episode_comments
    channel_id = request.args.get("channel_id")
    uid = _resolve_uid()
    eps = []
    for e in get_episodes(channel_id):
        row = annotate_episode_access(e, uid)
        eid = row.get("id", "")
        row["like_count"] = get_episode_like_count(eid)
        row["comment_count"] = len(get_episode_comments(eid, limit=999))
        row["audio_play_url"] = f"/api/podcast/episodes/{eid}/audio"
        eps.append(row)
    return jsonify({"success": True, "episodes": eps, "count": len(eps)}), 200


@podcast_bp.route("/api/podcast/episodes/<episode_id>", methods=["GET"])
def podcast_episode_detail(episode_id: str):
    from backend.services.podcast_service import get_episode, annotate_episode_access
    from backend.services.podcast_audio_service import check_episode_audio
    ep = get_episode(episode_id)
    if not ep:
        return jsonify({"success": False, "error": "episode_not_found"}), 404
    uid = _resolve_uid()
    row = annotate_episode_access(ep, uid)
    row["audio_play_url"] = f"/api/podcast/episodes/{episode_id}/audio"
    row["audio_check"] = check_episode_audio(ep)
    return jsonify({"success": True, "episode": row}), 200


@podcast_bp.route("/api/podcast/episodes/<episode_id>/play", methods=["POST"])
def podcast_play(episode_id: str):
    from backend.services.podcast_service import get_episode, record_view, user_has_unlock
    uid = _resolve_uid()
    ep = get_episode(episode_id)
    if not ep:
        return jsonify({"success": False, "error": "episode_not_found"}), 404
    if not user_has_unlock(uid, ep):
        return jsonify({
            "success": False,
            "error": "premium_required",
            "shop_item_id": ep.get("shop_item_id"),
        }), 403
    return jsonify(record_view(episode_id, uid, "play")), 200


@podcast_bp.route("/api/podcast/episodes/<episode_id>/view", methods=["POST"])
def podcast_view(episode_id: str):
    uid = _resolve_uid()
    from backend.services.podcast_service import record_view
    return jsonify(record_view(episode_id, uid, "view")), 200


@podcast_bp.route("/api/podcast/episodes/<episode_id>/share", methods=["POST"])
def podcast_share(episode_id: str):
    from backend.services.podcast_service import record_share
    data = request.get_json(silent=True) or {}
    platform = data.get("platform") or request.args.get("platform") or ""
    uid = _resolve_uid()
    return jsonify(record_share(episode_id, uid, platform)), 200


@podcast_bp.route("/api/podcast/episodes/<episode_id>/listen-complete", methods=["POST"])
def podcast_listen_complete(episode_id: str):
    from backend.services.podcast_crypto_rewards_service import award_listen_complete_reward
    uid = _resolve_uid()
    reward = award_listen_complete_reward(uid, episode_id)
    return jsonify({"success": True, "episode_id": episode_id, "crypto_reward": reward}), 200


@podcast_bp.route("/api/podcast/crypto-rewards", methods=["GET"])
def podcast_crypto_rewards():
    from backend.services.podcast_crypto_rewards_service import get_crypto_rewards_info
    uid = _resolve_uid()
    return jsonify(get_crypto_rewards_info(uid)), 200


@podcast_bp.route("/api/podcast/generate", methods=["POST"])
def podcast_generate():
    from backend.services.podcast_service import start_generate_job
    data = request.get_json(silent=True) or {}
    uid = _resolve_uid()
    result = start_generate_job(
        uid,
        topic=data.get("topic", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        channel_id=data.get("channel_id", "generator-intelligence"),
        encode_profile=data.get("encode_profile", "standard"),
        assigned_agent=data.get("assigned_agent", "podcast_producer_agent"),
    )
    return jsonify(result), 200 if result.get("success") else 400


@podcast_bp.route("/api/podcast/generate/<job_id>/progress", methods=["GET"])
def podcast_generate_progress(job_id: str):
    from backend.services.podcast_service import get_job_progress
    result = get_job_progress(job_id)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@podcast_bp.route("/api/podcast/encode-profiles", methods=["GET"])
def podcast_encode_profiles():
    from backend.services.podcast_encode_service import list_encode_profiles
    return jsonify({"success": True, "profiles": list_encode_profiles()}), 200


@podcast_bp.route("/api/podcast/customers", methods=["GET"])
def podcast_customers():
    from backend.services.podcast_service import get_customers
    limit = request.args.get("limit", 24, type=int)
    return jsonify(get_customers(limit=limit)), 200


@podcast_bp.route("/api/podcast/social-links", methods=["GET"])
def podcast_social_links():
    from backend.services.podcast_service import get_social_links
    episode_id = request.args.get("episode_id")
    return jsonify(get_social_links(episode_id)), 200


@podcast_bp.route("/api/podcast/shop/unlock", methods=["POST"])
def podcast_shop_unlock():
    from backend.services.podcast_service import purchase_episode_unlock
    data = request.get_json(silent=True) or {}
    uid = _resolve_uid()
    item_id = data.get("item_id") or ""
    if not item_id:
        return jsonify({"success": False, "error": "item_id required"}), 400
    result = purchase_episode_unlock(uid, item_id)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@podcast_bp.route("/api/podcast/assign-agent", methods=["POST"])
def podcast_assign_agent():
    from backend.services.podcast_service import assign_agent_to_user
    data = request.get_json(silent=True) or {}
    uid = _resolve_uid()
    agent_id = data.get("agent_id", "podcast_producer_agent")
    result = assign_agent_to_user(uid, agent_id)
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@podcast_bp.route("/api/podcast/agent-tools", methods=["GET"])
def podcast_agent_tools():
    from backend.services.podcast_agent_service import AGENT_TOOLS
    return jsonify({
        "success": True,
        "tools": AGENT_TOOLS,
        "note": "Mutating actions via /api/podcast/agent-action require approved=true.",
    }), 200


@podcast_bp.route("/api/podcast/agent-action", methods=["POST"])
def podcast_agent_action():
    from backend.services.podcast_agent_service import execute_agent_action
    data = request.get_json(silent=True) or {}
    if not data.get("user_id"):
        data["user_id"] = _resolve_uid()
    result = execute_agent_action(data)
    code = int(result.pop("http_status", 200))
    return jsonify(result), code


@podcast_bp.route("/api/podcast/agent-projects", methods=["GET"])
def podcast_agent_projects():
    import json
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data", "podcast_agent_projects.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"success": True, **data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@podcast_bp.route("/api/podcast/stats", methods=["GET"])
def podcast_stats():
    from backend.services.podcast_service import get_channels, get_episodes
    from backend.services.podcast_social_service import get_activity_feed
    channels = get_channels()
    episodes = get_episodes()
    total_views = sum(int(e.get("view_count") or 0) for e in episodes)
    total_plays = sum(int(e.get("play_count") or 0) for e in episodes)
    gi_count = sum(1 for e in episodes if e.get("generator_intelligence"))
    return jsonify({
        "success": True,
        "channels": len(channels),
        "episodes": len(episodes),
        "total_views": total_views,
        "total_plays": total_plays,
        "generator_intelligence_episodes": gi_count,
        "platforms": ["youtube", "facebook", "discord", "github"],
        "recent_activity": get_activity_feed(5),
    }), 200


@podcast_bp.route("/api/podcast/portal-lines", methods=["GET"])
def podcast_portal_lines():
    from backend.services.podcast_social_service import get_portal_lines
    site_id = request.args.get("site") or request.args.get("site_id")
    return jsonify(get_portal_lines(site_id)), 200


@podcast_bp.route("/api/podcast/episodes/<episode_id>/comments", methods=["GET"])
def podcast_episode_comments(episode_id: str):
    from backend.services.podcast_social_service import get_episode_comments, get_episode_like_count, user_liked_episode
    uid = _resolve_uid()
    limit = request.args.get("limit", 50, type=int)
    return jsonify({
        "success": True,
        "episode_id": episode_id,
        "comments": get_episode_comments(episode_id, limit=limit),
        "like_count": get_episode_like_count(episode_id),
        "user_liked": user_liked_episode(episode_id, uid),
    }), 200


@podcast_bp.route("/api/podcast/episodes/<episode_id>/comments", methods=["POST"])
def podcast_add_comment(episode_id: str):
    from backend.services.podcast_social_service import add_episode_comment
    data = request.get_json(silent=True) or {}
    uid = _resolve_uid()
    result = add_episode_comment(
        episode_id, uid, data.get("content", ""),
        platform=data.get("platform", ""),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@podcast_bp.route("/api/podcast/episodes/<episode_id>/like", methods=["POST"])
def podcast_like_episode(episode_id: str):
    from backend.services.podcast_social_service import like_episode
    uid = _resolve_uid()
    return jsonify(like_episode(episode_id, uid)), 200


@podcast_bp.route("/api/podcast/channels/<channel_id>/follow", methods=["POST"])
def podcast_follow_channel(channel_id: str):
    from backend.services.podcast_social_service import follow_channel
    uid = _resolve_uid()
    result = follow_channel(channel_id, uid)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@podcast_bp.route("/api/podcast/activity", methods=["GET"])
def podcast_activity():
    from backend.services.podcast_social_service import get_activity_feed
    limit = request.args.get("limit", 30, type=int)
    return jsonify({"success": True, "activity": get_activity_feed(limit=limit)}), 200


@podcast_bp.route("/api/podcast/sound-check", methods=["GET", "POST"])
def podcast_sound_check():
    from backend.services.podcast_audio_service import sound_check_all
    repair = request.method == "POST" or request.args.get("repair", "").lower() in ("1", "true")
    result = sound_check_all(repair=repair)
    return jsonify(result), 200


@podcast_bp.route("/api/podcast/sound-lab", methods=["GET"])
def podcast_sound_lab():
    from backend.services.podcast_audio_service import get_sound_lab
    return jsonify(get_sound_lab()), 200


@podcast_bp.route("/api/podcast/rss", methods=["GET"])
@podcast_bp.route("/api/podcast/rss.xml", methods=["GET"])
def podcast_rss():
    from flask import Response
    from backend.services.podcast_expansions_service import build_rss_feed
    xml = build_rss_feed()
    return Response(xml, mimetype="application/rss+xml")


@podcast_bp.route("/api/podcast/episodes/<episode_id>/transcript", methods=["GET"])
def podcast_transcript(episode_id: str):
    from backend.services.podcast_expansions_service import get_episode_transcript
    result = get_episode_transcript(episode_id)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@podcast_bp.route("/api/podcast/episodes/<episode_id>/chapters", methods=["GET"])
def podcast_chapters(episode_id: str):
    from backend.services.podcast_expansions_service import get_episode_chapters
    result = get_episode_chapters(episode_id)
    code = 200 if result.get("success") else 404
    return jsonify(result), code


@podcast_bp.route("/api/podcast/leaderboard", methods=["GET"])
def podcast_leaderboard():
    from backend.services.podcast_expansions_service import get_leaderboard
    limit = request.args.get("limit", 20, type=int)
    return jsonify(get_leaderboard(limit=limit)), 200


@podcast_bp.route("/api/podcast/episodes/<episode_id>/audio", methods=["GET"])
def podcast_stream_audio(episode_id: str):
    from flask import send_file, abort
    from backend.services.podcast_audio_service import stream_episode_path
    path = stream_episode_path(episode_id)
    if not path:
        return jsonify({"success": False, "error": "audio_unavailable"}), 404
    mimetype = "audio/mpeg" if path.lower().endswith(".mp3") else "audio/wav"
    if path.lower().endswith(".m4a"):
        mimetype = "audio/mp4"
    elif path.lower().endswith(".opus"):
        mimetype = "audio/opus"
    return send_file(path, mimetype=mimetype, conditional=True)


@podcast_bp.route("/api/podcast/news", methods=["GET"])
def podcast_news_feed():
    from backend.services.podcast_social_service import get_news_feed
    limit = request.args.get("limit", 20, type=int)
    return jsonify({"success": True, "news": get_news_feed(limit=limit)}), 200


@podcast_bp.route("/api/podcast/news/<news_id>/comments", methods=["GET"])
def podcast_news_comments(news_id: str):
    from backend.services.podcast_social_service import get_news_comments
    limit = request.args.get("limit", 50, type=int)
    return jsonify({
        "success": True,
        "news_id": news_id,
        "comments": get_news_comments(news_id, limit=limit),
    }), 200


@podcast_bp.route("/api/podcast/news/<news_id>/comments", methods=["POST"])
def podcast_news_add_comment(news_id: str):
    from backend.services.podcast_social_service import add_news_comment
    data = request.get_json(silent=True) or {}
    uid = _resolve_uid()
    result = add_news_comment(news_id, uid, data.get("content", ""))
    code = 200 if result.get("success") else 400
    return jsonify(result), code
