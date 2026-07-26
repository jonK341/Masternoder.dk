"""YouTube + OBS agent tools for 5D fleet progress monitor streaming."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "youtube_stream_agent.json")

AGENT_TOOLS: List[Dict[str, Any]] = [
    {
        "action": "stream_urls",
        "method": "GET",
        "path": "/api/exchange/youtube-stream/controls",
        "mutating": False,
        "description": "OBS / YouTube capture URLs for fleet monitor and streamer hub.",
    },
    {
        "action": "monitor_status",
        "method": "GET",
        "path": "/api/exchange/fleet-progress-monitor/public?light=1",
        "mutating": False,
        "description": "Audience-safe fleet monitor snapshot for live overlays.",
    },
    {
        "action": "scene_guide",
        "method": "GET",
        "path": "/api/exchange/youtube-stream/controls",
        "mutating": False,
        "description": "OBS scene presets and go-live checklist.",
    },
    {
        "action": "assign_agent",
        "method": "POST",
        "path": "/api/exchange/youtube-stream/assign-agent",
        "mutating": True,
        "params": ["user_id", "agent_id"],
        "description": "Assign youtube_stream_agent skill set to operator.",
    },
    {
        "action": "preflight_urls",
        "method": "POST",
        "path": "/api/exchange/youtube-stream/agent-action",
        "mutating": True,
        "description": "Agent checks monitor + stream pages are reachable (same origin).",
    },
    {
        "action": "compose_chapter",
        "method": "GET",
        "path": "/api/exchange/fleet-stream/composer",
        "mutating": False,
        "description": "Current rotating stream chapter with decoded AI content.",
    },
    {
        "action": "narration_line",
        "method": "GET",
        "path": "/api/exchange/youtube-stream/agent-action",
        "mutating": False,
        "description": "Latest public narration line for YouTube voice overlay.",
    },
]


def _load_config() -> Dict[str, Any]:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _public_base(base_url: Optional[str] = None) -> str:
    raw = (base_url or os.environ.get("PUBLIC_SITE_URL") or "").strip()
    return raw.rstrip("/") if raw else ""


def _abs(base: str, path: str) -> str:
    if not base:
        return path
    return base.rstrip("/") + path


def stream_controls(*, base_url: Optional[str] = None) -> Dict[str, Any]:
    cfg = _load_config()
    base = _public_base(base_url)
    from backend.services.fleet_stream_chat_service import live_config, youtube_public_urls

    live = live_config()
    yt_urls = youtube_public_urls(live)
    channel = (
        os.environ.get("YOUTUBE_CHANNEL_URL", "").strip()
        or live.get("youtube_channel_url")
        or "https://youtube.com/@MasterNoder"
    )
    obs_cfg = live.get("obs") if isinstance(live.get("obs"), dict) else {}
    stream_meta = live.get("stream") if isinstance(live.get("stream"), dict) else {}
    return {
        "success": True,
        "primary_agent": cfg.get("primary_agent") or "youtube_stream_agent",
        "agents": cfg.get("agents") or [],
        "skill_set": cfg.get("skill_set") or [],
        "obs_scenes": cfg.get("obs_scenes") or [],
        "checklist": cfg.get("checklist") or [],
        "live_broadcast": {
            "title": stream_meta.get("title") or "",
            "video_id": yt_urls.get("video_id") or "",
            "watch_url": yt_urls.get("watch_url") or "",
            "studio_url": yt_urls.get("studio_url") or "",
            "embed_url": yt_urls.get("embed_url") or "",
        },
        "monitor": {
            "full": _abs(base, "/fleet-progress-monitor/"),
            "stream_layout": _abs(base, "/fleet-progress-monitor/?mode=stream"),
            "fleet_stream_alias": _abs(base, "/fleet-stream/"),
            "streamer_hub": _abs(base, "/streamer/"),
            "obs_browser": _abs(base, "/streamer/?obs=1"),
            "public_api": _abs(base, "/api/exchange/fleet-progress-monitor/public?light=1"),
        },
        "youtube": {
            "channel_url": channel,
            "studio_live_url": yt_urls.get("studio_url") or "https://studio.youtube.com/",
            "watch_url": yt_urls.get("watch_url") or "",
            "video_id": yt_urls.get("video_id") or "",
            "ingest_note": "Create stream in YouTube Studio → paste RTMP key in OBS (never commit keys).",
            "recommended": obs_cfg.get("resolution", "1920×1080")
            + " · "
            + str(obs_cfg.get("fps", 30))
            + "fps · browser source for 5D canvas",
        },
        "podcast": {
            "hub": _abs(base, "/streamer/"),
            "episodes": _abs(base, "/podcast#episodes"),
            "news_comments": _abs(base, "/podcast#news"),
        },
    }


def assign_youtube_stream_agents(user_id: str, agent_id: str = "youtube_stream_agent") -> Dict[str, Any]:
    try:
        from backend.services.user_agent_skills import UserAgentSkills

        svc = UserAgentSkills()
        skills = svc.get_user_skills(user_id)
        agents = list(skills.get("assigned_agents") or [])
        for aid in ("youtube_stream_agent", "podcast_producer_agent", "reporter_agent"):
            if aid not in agents:
                agents.append(aid)
        skills["assigned_agents"] = agents
        skills["skill_path"] = "youtube_stream"
        skill_list = list(skills.get("skills") or [])
        new_skills = [
            {"agent_id": "youtube_stream_agent", "skill": "obs_browser_capture", "level": 1},
            {"agent_id": "youtube_stream_agent", "skill": "youtube_live_preflight", "level": 1},
            {"agent_id": "youtube_stream_agent", "skill": "fleet_monitor_scene", "level": 1},
            {"agent_id": "youtube_stream_agent", "skill": "stream_url_playbook", "level": 1},
            {"agent_id": "podcast_producer_agent", "skill": "youtube_syndicate", "level": 1},
            {"agent_id": "reporter_agent", "skill": "broadcast", "level": 1},
            {"agent_id": "reporter_agent", "skill": "live_ticker_narration", "level": 1},
            {"agent_id": "content_generator_agent", "skill": "ai_stream_title", "level": 1},
        ]
        if agent_id and agent_id not in {s["agent_id"] for s in new_skills}:
            new_skills.append({"agent_id": agent_id, "skill": "stream_url_playbook", "level": 1})
        existing = {(s.get("agent_id"), s.get("skill")) for s in skill_list}
        for ns in new_skills:
            key = (ns["agent_id"], ns["skill"])
            if key not in existing:
                skill_list.append(ns)
        skills["skills"] = skill_list
        svc.save_user_skills(user_id, skills)
        return {
            "success": True,
            "user_id": user_id,
            "assigned_agents": agents,
            "skill_path": "youtube_stream",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _monitor_narration_line() -> str:
    from backend.services.exchange_fleet_progress_monitor_service import public_fleet_progress_monitor

    try:
        payload = public_fleet_progress_monitor(light=True)
        narr = (payload or {}).get("narration") or []
        if narr and isinstance(narr[0], dict):
            return str(narr[0].get("text") or narr[0].get("line") or "")
        if narr and isinstance(narr[0], str):
            return narr[0]
        ps = (payload or {}).get("progression") or {}
        fl = (payload or {}).get("fleet") or {}
        return (
            f"Commander level {ps.get('commander_level', 1)} — "
            f"{ps.get('fleet_total_xp', 0)} fleet XP — {fl.get('bot_count', 0)} bots on lane."
        )
    except Exception:
        return "Fleet monitor telemetry online — audience-safe stream."


def execute_agent_action(body: Dict[str, Any], *, base_url: Optional[str] = None) -> Dict[str, Any]:
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

    uid = str(body.get("user_id") or "default_user").strip()

    if action == "stream_urls" or action == "scene_guide":
        return {**stream_controls(base_url=base_url), "http_status": 200}
    if action == "monitor_status":
        from backend.services.exchange_fleet_progress_monitor_service import (
            monitor_public_enabled,
            public_fleet_progress_monitor,
        )

        if not monitor_public_enabled():
            return {"success": False, "error": "monitor_disabled", "http_status": 404}
        return {"success": True, "monitor": public_fleet_progress_monitor(light=True), "http_status": 200}
    if action == "assign_agent":
        return {
            **assign_youtube_stream_agents(uid, body.get("agent_id") or "youtube_stream_agent"),
            "http_status": 200,
        }
    if action == "preflight_urls":
        import urllib.request

        ctrl = stream_controls(base_url=base_url)
        urls = list((ctrl.get("monitor") or {}).values())
        results = []
        for url in urls:
            if not url or not str(url).startswith("http"):
                continue
            ok = False
            code = 0
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=12) as resp:
                    code = resp.getcode()
                    ok = 200 <= code < 400
            except Exception as exc:
                results.append({"url": url, "ok": False, "error": str(exc)[:120]})
                continue
            results.append({"url": url, "ok": ok, "status": code})
        return {"success": True, "checks": results, "http_status": 200}
    if action == "narration_line":
        return {"success": True, "line": _monitor_narration_line(), "http_status": 200}
    if action == "compose_chapter":
        from backend.services.fleet_stream_composer_service import list_chapters_public
        from backend.services.exchange_fleet_progress_monitor_service import public_fleet_progress_monitor

        snap = public_fleet_progress_monitor(light=True)
        return {**list_chapters_public(snap, stream_mode=True), "http_status": 200}

    return {"success": False, "error": "not_implemented", "http_status": 501}
