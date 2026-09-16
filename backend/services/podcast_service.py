"""Podcast service — channels, episodes, views, AI generation, shop unlocks."""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CHANNELS_FILE = os.path.join(_BASE, "data", "podcast_channels.json")
_EPISODES_FILE = os.path.join(_BASE, "data", "podcast_episodes.json")
_CUSTOMERS_FILE = os.path.join(_BASE, "data", "podcast_customers.json")
_JOBS_FILE = os.path.join(_BASE, "data", "podcast_jobs.json")
_PLAYS_LOG = os.path.join(_BASE, "logs", "podcast_plays.jsonl")


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


def _append_log(path: str, record: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def get_channels() -> List[Dict[str, Any]]:
    data = _read_json(_CHANNELS_FILE)
    return list(data.get("channels") or [])


def get_channel(channel_id: str) -> Optional[Dict[str, Any]]:
    return next((c for c in get_channels() if c.get("id") == channel_id), None)


def get_episodes(channel_id: Optional[str] = None) -> List[Dict[str, Any]]:
    data = _read_json(_EPISODES_FILE)
    eps = list(data.get("episodes") or [])
    if channel_id:
        eps = [e for e in eps if e.get("channel_id") == channel_id]
    return sorted(eps, key=lambda e: e.get("published_at") or "", reverse=True)


def get_episode(episode_id: str) -> Optional[Dict[str, Any]]:
    return next((e for e in get_episodes() if e.get("id") == episode_id), None)


def _save_episodes(episodes: List[Dict[str, Any]]) -> None:
    data = _read_json(_EPISODES_FILE)
    data["episodes"] = episodes
    data["updated_at"] = _iso()[:10]
    _write_json(_EPISODES_FILE, data)


def user_has_unlock(user_id: str, episode: Dict[str, Any]) -> bool:
    if not episode.get("premium"):
        return True
    shop_item = episode.get("shop_item_id")
    if not shop_item:
        return False
    try:
        from backend.services.shop_db_service import get_inventory
        inv = get_inventory(user_id) or []
        for item in inv:
            iid = str(item.get("item_id") or "")
            if iid == shop_item or iid == f"podcast-unlock-{episode.get('id')}":
                return True
        if shop_item == "podcast-pro-pass":
            for item in inv:
                if str(item.get("item_id") or "") == "podcast-pro-pass":
                    return True
    except Exception:
        pass
    return False


def annotate_episode_access(episode: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    out = dict(episode)
    out["unlocked"] = user_has_unlock(user_id, episode)
    out["requires_premium"] = bool(episode.get("premium"))
    return out


def record_view(episode_id: str, user_id: str, action: str = "view") -> Dict[str, Any]:
    with _LOCK:
        data = _read_json(_EPISODES_FILE)
        episodes = list(data.get("episodes") or [])
        ep = next((e for e in episodes if e.get("id") == episode_id), None)
        if not ep:
            return {"success": False, "error": "episode_not_found"}

        if action == "play":
            ep["play_count"] = int(ep.get("play_count") or 0) + 1
        ep["view_count"] = int(ep.get("view_count") or 0) + 1
        _save_episodes(episodes)

        _append_log(_PLAYS_LOG, {
            "episode_id": episode_id,
            "user_id": user_id,
            "action": action,
            "view_count": ep["view_count"],
            "play_count": ep.get("play_count"),
            "at": _iso(),
        })

    reward = {}
    try:
        from backend.services.podcast_crypto_rewards_service import (
            award_play_reward,
            award_view_milestone_reward,
        )
        if action == "play":
            reward = award_play_reward(user_id, episode_id)
        milestone = award_view_milestone_reward(user_id, episode_id, ep["view_count"])
        if milestone.get("awarded_mn2"):
            reward["milestone"] = milestone
    except Exception as e:
        reward = {"error": str(e)}

    return {
        "success": True,
        "episode_id": episode_id,
        "view_count": ep["view_count"],
        "play_count": ep.get("play_count"),
        "crypto_reward": reward,
    }


def record_share(episode_id: str, user_id: str, platform: str = "") -> Dict[str, Any]:
    with _LOCK:
        data = _read_json(_EPISODES_FILE)
        episodes = list(data.get("episodes") or [])
        ep = next((e for e in episodes if e.get("id") == episode_id), None)
        if not ep:
            return {"success": False, "error": "episode_not_found"}
        ep["share_count"] = int(ep.get("share_count") or 0) + 1
        _save_episodes(episodes)

    reward = {}
    try:
        from backend.services.podcast_crypto_rewards_service import award_share_reward
        reward = award_share_reward(user_id, episode_id, platform)
    except Exception as e:
        reward = {"error": str(e)}

    return {
        "success": True,
        "episode_id": episode_id,
        "share_count": ep["share_count"],
        "platform": platform,
        "crypto_reward": reward,
    }


def get_customers(limit: int = 24) -> Dict[str, Any]:
    data = _read_json(_CUSTOMERS_FILE)
    customers = list(data.get("customers") or [])[:limit]
    return {
        "success": True,
        "total_partners": data.get("total_partners", len(customers)),
        "total_listeners": data.get("total_listeners", 0),
        "customers": customers,
        "note": "Major brands using MasterNoder Podcast — a very popular idea.",
    }


def get_social_links(episode_id: Optional[str] = None) -> Dict[str, Any]:
    networks = []
    try:
        path = os.path.join(_BASE, "data", "social_networks.json")
        networks = _read_json(path).get("networks") or []
    except Exception:
        pass

    episode_links = {}
    if episode_id:
        ep = get_episode(episode_id)
        if ep:
            episode_links = ep.get("platform_links") or {}

    return {
        "success": True,
        "networks": networks,
        "episode_links": episode_links,
        "platforms": ["youtube", "facebook", "discord", "github"],
    }


def _generate_script(topic: str, title: str, description: str) -> str:
    """Generate podcast script — LLM when available, template fallback."""
    t = (topic or title or "MasterNoder").strip()
    desc = (description or "").strip()
    try:
        from backend.services.video_generator_service import _ai_generate_enhanced_descriptions
        ai = _ai_generate_enhanced_descriptions(t, desc or t, segment_count=4)
        if ai and isinstance(ai, list) and len(ai) >= 2:
            parts = [f"Welcome to MasterNoder Podcast. Today: {title or t}."]
            for i, seg in enumerate(ai[:4], 1):
                text = seg if isinstance(seg, str) else (seg.get("description") or seg.get("text") or "")
                if text:
                    parts.append(f"Segment {i}. {text}")
            parts.append("Thanks for listening. Earn MN2 crypto rewards by playing and sharing episodes.")
            return "\n\n".join(parts)
    except Exception:
        pass
    return (
        f"Welcome to MasterNoder Podcast.\n\n"
        f"Today we explore {title or t}. {desc}\n\n"
        f"This episode was made with generator intelligence — AI script, TTS narration, and AI audio encoding.\n\n"
        f"Share on YouTube, Facebook, Discord, and GitHub to earn crypto rewards.\n\n"
        f"Thanks for listening."
    )


def _load_jobs() -> Dict[str, Any]:
    return _read_json(_JOBS_FILE)


def _save_jobs(jobs: Dict[str, Any]) -> None:
    _write_json(_JOBS_FILE, jobs)


def start_generate_job(
    user_id: str,
    *,
    topic: str = "",
    title: str = "",
    description: str = "",
    channel_id: str = "generator-intelligence",
    encode_profile: str = "standard",
    assigned_agent: str = "podcast_producer_agent",
) -> Dict[str, Any]:
    job_id = f"pod-{uuid.uuid4().hex[:12]}"
    script = _generate_script(topic, title, description)
    job = {
        "job_id": job_id,
        "user_id": user_id,
        "status": "queued",
        "progress": 0,
        "topic": topic,
        "title": title or topic or "AI Generated Episode",
        "description": description,
        "channel_id": channel_id,
        "encode_profile": encode_profile,
        "assigned_agent": assigned_agent,
        "script_preview": script[:500],
        "generator_intelligence": True,
        "created_at": _iso(),
        "updated_at": _iso(),
    }
    with _LOCK:
        jobs = _load_jobs()
        jobs[job_id] = job
        _save_jobs(jobs)

    thread = threading.Thread(
        target=_run_generate_job,
        args=(job_id, user_id, script, title or topic, description, channel_id, encode_profile, assigned_agent),
        daemon=True,
    )
    thread.start()
    return {"success": True, "job_id": job_id, "status": "queued"}


def _run_generate_job(
    job_id: str,
    user_id: str,
    script: str,
    title: str,
    description: str,
    channel_id: str,
    encode_profile: str,
    assigned_agent: str,
) -> None:
    def _update(**kwargs: Any) -> None:
        with _LOCK:
            jobs = _load_jobs()
            rec = jobs.get(job_id) or {}
            rec.update(kwargs)
            rec["updated_at"] = _iso()
            jobs[job_id] = rec
            _save_jobs(jobs)

    _update(status="scripting", progress=20)
    time.sleep(0.3)
    _update(status="tts", progress=45)

    from backend.services.podcast_encode_service import generate_episode_audio
    eid = f"gen-{job_id[-8:]}"
    audio_result = generate_episode_audio(
        script,
        profile=encode_profile,
        episode_id=eid,
    )

    if not audio_result.get("success"):
        _update(status="failed", progress=100, error=audio_result.get("error"))
        return

    _update(status="encoding", progress=75)
    episode = {
        "id": eid,
        "channel_id": channel_id,
        "title": title or "AI Generated Episode",
        "description": description or f"Generated with generator intelligence ({encode_profile}).",
        "duration_sec": audio_result.get("duration_sec_estimate", 300),
        "audio_url": audio_result.get("audio_url", ""),
        "published_at": _iso(),
        "view_count": 0,
        "play_count": 0,
        "share_count": 0,
        "premium": False,
        "shop_item_id": None,
        "generator_intelligence": True,
        "encode_profile": encode_profile,
        "assigned_agent": assigned_agent,
        "tags": ["ai-generated", "generator-intelligence"],
        "platform_links": {},
        "job_id": job_id,
    }

    with _LOCK:
        data = _read_json(_EPISODES_FILE)
        episodes = list(data.get("episodes") or [])
        episodes.insert(0, episode)
        _save_episodes(episodes)

    reward = {}
    try:
        from backend.services.podcast_crypto_rewards_service import award_generate_reward
        reward = award_generate_reward(user_id, job_id)
    except Exception:
        pass

    _update(
        status="completed",
        progress=100,
        episode_id=eid,
        audio_url=audio_result.get("audio_url"),
        crypto_reward=reward,
    )


def get_job_progress(job_id: str) -> Dict[str, Any]:
    jobs = _load_jobs()
    job = jobs.get(job_id)
    if not job:
        return {"success": False, "error": "job_not_found"}
    return {"success": True, **job}


def assign_agent_to_user(user_id: str, agent_id: str = "podcast_producer_agent") -> Dict[str, Any]:
    try:
        from backend.services.user_agent_skills import UserAgentSkills
        svc = UserAgentSkills()
        skills = svc.get_user_skills(user_id)
        agents = list(skills.get("assigned_agents") or [])
        if agent_id not in agents:
            agents.append(agent_id)
        skills["assigned_agents"] = agents
        skills["skill_path"] = "podcast"
        skill_list = list(skills.get("skills") or [])
        new_skills = [
            {"agent_id": "podcast_producer_agent", "skill": "generate_episode", "level": 1},
            {"agent_id": "podcast_producer_agent", "skill": "encode_audio", "level": 1},
            {"agent_id": "podcast_producer_agent", "skill": "distribute_episode", "level": 1},
            {"agent_id": "content_generator_agent", "skill": "ai_podcast_script", "level": 1},
            {"agent_id": "reporter_agent", "skill": "broadcast", "level": 1},
        ]
        existing = {(s.get("agent_id"), s.get("skill")) for s in skill_list}
        for ns in new_skills:
            key = (ns["agent_id"], ns["skill"])
            if key not in existing:
                skill_list.append(ns)
        skills["skills"] = skill_list
        svc.save_user_skills(user_id, skills)
        return {"success": True, "user_id": user_id, "assigned_agents": agents, "skill_path": "podcast"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def purchase_episode_unlock(user_id: str, item_id: str) -> Dict[str, Any]:
    from backend.services.shop_mn2_purchase_core import purchase_with_mn2_balance
    body, status = purchase_with_mn2_balance(user_id, item_id)
    if status == 200 and body.get("success"):
        try:
            from backend.services.shop_db_service import add_to_inventory
            add_to_inventory(user_id, item_id, 1)
        except Exception:
            pass
    return body
