"""Podcast agent-native tools and action executor."""
from __future__ import annotations

from typing import Any, Dict, List

AGENT_TOOLS: List[Dict[str, Any]] = [
    {
        "action": "list_channels",
        "method": "GET",
        "path": "/api/podcast/channels",
        "mutating": False,
        "description": "List podcast channels with YouTube, Facebook, Discord, GitHub links.",
    },
    {
        "action": "list_episodes",
        "method": "GET",
        "path": "/api/podcast/episodes",
        "mutating": False,
        "params": ["channel_id", "user_id"],
        "description": "List episodes; optional channel filter.",
    },
    {
        "action": "get_episode",
        "method": "GET",
        "path": "/api/podcast/episodes/<episode_id>",
        "mutating": False,
        "params": ["episode_id", "user_id"],
        "description": "Episode detail with unlock status.",
    },
    {
        "action": "play",
        "method": "POST",
        "path": "/api/podcast/episodes/<episode_id>/play",
        "mutating": True,
        "params": ["episode_id", "user_id"],
        "description": "Record play + view count; award MN2 crypto reward.",
    },
    {
        "action": "share",
        "method": "POST",
        "path": "/api/podcast/episodes/<episode_id>/share",
        "mutating": True,
        "params": ["episode_id", "user_id", "platform"],
        "description": "Record share to YouTube/Facebook/Discord/GitHub; MN2 reward.",
    },
    {
        "action": "generate",
        "method": "POST",
        "path": "/api/podcast/generate",
        "mutating": True,
        "params": ["user_id", "topic", "title", "encode_profile", "assigned_agent"],
        "description": "Start AI podcast generation (generator intelligence + AI encoder).",
    },
    {
        "action": "progress",
        "method": "GET",
        "path": "/api/podcast/generate/<job_id>/progress",
        "mutating": False,
        "params": ["job_id"],
        "description": "Poll generation job progress.",
    },
    {
        "action": "encode_profiles",
        "method": "GET",
        "path": "/api/podcast/encode-profiles",
        "mutating": False,
        "description": "AI audio encoder profiles (standard/premium/ultra).",
    },
    {
        "action": "crypto_rewards",
        "method": "GET",
        "path": "/api/podcast/crypto-rewards",
        "mutating": False,
        "params": ["user_id"],
        "description": "MN2 earn rates for play, share, listen, generate.",
    },
    {
        "action": "shop_unlock",
        "method": "POST",
        "path": "/api/podcast/shop/unlock",
        "mutating": True,
        "params": ["user_id", "item_id"],
        "description": "Buy premium episode unlock with MN2 from shop.",
    },
    {
        "action": "assign_agent",
        "method": "POST",
        "path": "/api/podcast/assign-agent",
        "mutating": True,
        "params": ["user_id", "agent_id"],
        "description": "Assign podcast_producer_agent to user.",
    },
    {
        "action": "customers",
        "method": "GET",
        "path": "/api/podcast/customers",
        "mutating": False,
        "description": "Enterprise customers using MasterNoder Podcast.",
    },
    {
        "action": "comment",
        "method": "POST",
        "path": "/api/podcast/episodes/<episode_id>/comments",
        "mutating": True,
        "params": ["episode_id", "user_id", "content"],
        "description": "Add episode comment; MN2 crypto reward.",
    },
    {
        "action": "like",
        "method": "POST",
        "path": "/api/podcast/episodes/<episode_id>/like",
        "mutating": True,
        "params": ["episode_id", "user_id"],
        "description": "Like an episode.",
    },
    {
        "action": "follow_channel",
        "method": "POST",
        "path": "/api/podcast/channels/<channel_id>/follow",
        "mutating": True,
        "params": ["channel_id", "user_id"],
        "description": "Follow a podcast channel.",
    },
    {
        "action": "activity",
        "method": "GET",
        "path": "/api/podcast/activity",
        "mutating": False,
        "description": "Recent podcast social activity feed.",
    },
    {
        "action": "portal_lines",
        "method": "GET",
        "path": "/api/podcast/portal-lines",
        "mutating": False,
        "params": ["site"],
        "description": "Cross-site portal lines and comment hints.",
    },
]


def execute_agent_action(body: Dict[str, Any]) -> Dict[str, Any]:
    action = (body.get("action") or "").strip()
    tool = next((t for t in AGENT_TOOLS if t["action"] == action), None)
    if not tool:
        return {
            "success": False,
            "error": "Unknown action",
            "available": [t["action"] for t in AGENT_TOOLS],
            "http_status": 400,
        }
    if tool["mutating"] and not body.get("approved"):
        return {
            "success": False,
            "error": "Mutating action requires approved=true",
            "action": action,
            "http_status": 403,
        }

    from backend.services import podcast_service as ps

    uid = str(body.get("user_id") or "default_user").strip()

    if action == "list_channels":
        return {"success": True, "channels": ps.get_channels(), "http_status": 200}
    if action == "list_episodes":
        eps = ps.get_episodes(body.get("channel_id"))
        return {
            "success": True,
            "episodes": [ps.annotate_episode_access(e, uid) for e in eps],
            "http_status": 200,
        }
    if action == "get_episode":
        eid = body.get("episode_id") or ""
        ep = ps.get_episode(eid)
        if not ep:
            return {"success": False, "error": "not_found", "http_status": 404}
        return {"success": True, "episode": ps.annotate_episode_access(ep, uid), "http_status": 200}
    if action == "play":
        return {**ps.record_view(body.get("episode_id", ""), uid, "play"), "http_status": 200}
    if action == "share":
        return {**ps.record_share(body.get("episode_id", ""), uid, body.get("platform", "")), "http_status": 200}
    if action == "generate":
        return {**ps.start_generate_job(
            uid,
            topic=body.get("topic", ""),
            title=body.get("title", ""),
            description=body.get("description", ""),
            channel_id=body.get("channel_id", "generator-intelligence"),
            encode_profile=body.get("encode_profile", "standard"),
            assigned_agent=body.get("assigned_agent", "podcast_producer_agent"),
        ), "http_status": 200}
    if action == "progress":
        return {**ps.get_job_progress(body.get("job_id", "")), "http_status": 200}
    if action == "encode_profiles":
        from backend.services.podcast_encode_service import list_encode_profiles
        return {"success": True, "profiles": list_encode_profiles(), "http_status": 200}
    if action == "crypto_rewards":
        from backend.services.podcast_crypto_rewards_service import get_crypto_rewards_info
        return {**get_crypto_rewards_info(uid), "http_status": 200}
    if action == "shop_unlock":
        result = ps.purchase_episode_unlock(uid, body.get("item_id", ""))
        code = 200 if result.get("success") else 400
        return {**result, "http_status": code}
    if action == "assign_agent":
        return {**ps.assign_agent_to_user(uid, body.get("agent_id", "podcast_producer_agent")), "http_status": 200}
    if action == "customers":
        return {**ps.get_customers(), "http_status": 200}
    if action == "comment":
        from backend.services.podcast_social_service import add_episode_comment
        return {**add_episode_comment(body.get("episode_id", ""), uid, body.get("content", "")), "http_status": 200}
    if action == "like":
        from backend.services.podcast_social_service import like_episode
        return {**like_episode(body.get("episode_id", ""), uid), "http_status": 200}
    if action == "follow_channel":
        from backend.services.podcast_social_service import follow_channel
        return {**follow_channel(body.get("channel_id", ""), uid), "http_status": 200}
    if action == "activity":
        from backend.services.podcast_social_service import get_activity_feed
        return {"success": True, "activity": get_activity_feed(), "http_status": 200}
    if action == "portal_lines":
        from backend.services.podcast_social_service import get_portal_lines
        return {**get_portal_lines(body.get("site")), "http_status": 200}

    return {"success": False, "error": "not_implemented", "http_status": 501}
