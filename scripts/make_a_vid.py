#!/usr/bin/env python3
"""
Make one long video with full context: profile (AI/user), service worker & agents.
Gathers profile, agent connections, and agent groups; builds segments with pictures and sound.
Run from project root:  python scripts/make_a_vid.py
"""
import os
import sys
import json
import uuid

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)


def gather_all_context(user_id: str = "default_user") -> dict:
    """Gather context from profile, service worker (API paths), and agents."""
    ctx = {
        "user_id": user_id,
        "profile": None,
        "profile_display": None,
        "agent_connections": [],
        "agent_groups": {},
        "service_worker_context": {
            "cache_name": "vidgenerator-sw-v3",
            "api_prefixes": [
                "/vidgenerator/api/generator/",
                "/vidgenerator/api/documentary/",
                "/vidgenerator/api/unified/",
                "/vidgenerator/api/ai-clips/",
            ],
            "role": "offline queue, generator progress, agent API",
        },
    }

    # Profile (AI / user profile from backend)
    try:
        from backend.services.user_profile import UserProfile
        up = UserProfile()
        ctx["profile_display"] = up.get_profile_display(user_id)
        if ctx["profile_display"] and ctx["profile_display"].get("success"):
            ctx["profile"] = ctx["profile_display"].get("profile", {})
    except Exception as e:
        ctx["profile_error"] = str(e)

    # Agent–generator connections (20 integration points)
    try:
        from backend.services.generator_agent_connections import get_connections
        ctx["agent_connections"] = get_connections()
    except Exception as e:
        ctx["agent_connections_error"] = str(e)

    # Agent groups (service workers + agents from logs)
    try:
        groups_path = os.path.join(_root, "logs", "agent_groups", "groups.json")
        if os.path.isfile(groups_path):
            with open(groups_path, "r", encoding="utf-8") as f:
                ctx["agent_groups"] = json.load(f)
    except Exception as e:
        ctx["agent_groups_error"] = str(e)

    return ctx


def context_to_segments(ctx: dict, short: bool = False) -> list:
    """Turn gathered context into video segments (title, description, duration)."""
    segments = []

    # Intro: title
    segments.append({
        "title": "Context & Content Video",
        "description": "Profile, service worker, and agents.",
        "duration": 4,
    })

    if short:
        segments.append({
            "title": "Profile + Agents",
            "description": "Full context from make_a_vid.py",
            "duration": 5,
        })
        segments.append({
            "title": "End",
            "description": "Generated with make_a_vid.py",
            "duration": 3,
        })
        return segments

    # Profile
    profile = ctx.get("profile") or {}
    if profile:
        display_name = profile.get("display_name") or profile.get("username") or ctx.get("user_id", "User")
        segments.append({
            "title": f"Profile: {display_name}",
            "description": profile.get("bio") or "Profile context from backend.",
            "duration": 4,
        })
        if profile.get("skill_path"):
            segments.append({
                "title": f"Skill path: {profile.get('skill_path')}",
                "description": "Agent skillset and preferences.",
                "duration": 3,
            })
    else:
        segments.append({
            "title": "Profile context",
            "description": "User profile (default or from API).",
            "duration": 3,
        })

    # Service worker context
    sw = ctx.get("service_worker_context", {})
    segments.append({
        "title": "Service worker",
        "description": sw.get("role", "Generator APIs, offline queue, progress."),
        "duration": 4,
    })

    # Agent connections (first 10 as segments to keep length reasonable)
    connections = ctx.get("agent_connections") or []
    for i, c in enumerate(connections[:10]):
        segments.append({
            "title": c.get("agent", "Agent"),
            "description": (c.get("description") or "")[:80],
            "duration": 3,
        })

    # Agent groups (maintenance, development, etc.)
    groups = ctx.get("agent_groups") or {}
    for name, data in list(groups.items())[:4]:
        if isinstance(data, dict):
            desc = data.get("description", name)
            members = data.get("members", {})
            agent_count = sum(len(v) if isinstance(v, list) else 0 for v in members.values())
            segments.append({
                "title": data.get("name", name),
                "description": f"{desc}. Members: {agent_count}.",
                "duration": 4,
            })

    # Outro
    segments.append({
        "title": "End",
        "description": "Generated with make_a_vid.py — profile, SW & agents.",
        "duration": 4,
    })

    return segments


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Make one long video with profile, SW & agents context")
    ap.add_argument("--short", action="store_true", help="Fewer segments (3 only) for quick test")
    ap.add_argument("--no-audio", action="store_true", help="Skip adding silent audio track")
    args = ap.parse_args()

    user_id = os.environ.get("VID_USER_ID", "default_user")

    print("Gathering all context (profile, service worker, agents)...")
    ctx = gather_all_context(user_id)
    print(f"  Profile: {'OK' if ctx.get('profile') else 'default'}")
    print(f"  Agent connections: {len(ctx.get('agent_connections') or [])}")
    print(f"  Agent groups: {len(ctx.get('agent_groups') or {})}")

    segments = context_to_segments(ctx, short=args.short)
    print(f"  Segments: {len(segments)}")

    doc_id = str(uuid.uuid4())
    print(f"\nMaking long video (pictures + sound)...")
    print(f"  doc_id = {doc_id}")

    from backend.services.video_generator_service import (
        generate_rich_video_sync,
        VIDEOS_DIR,
    )

    def progress(percent, msg):
        print(f"  [{percent}%] {msg}")

    path, err = generate_rich_video_sync(
        doc_id,
        segments,
        width=1280,
        height=768,
        add_audio=not args.no_audio,
        on_progress=progress,
    )

    if path and os.path.isfile(path):
        size = os.path.getsize(path)
        print(f"\nOK   Video saved: {path}")
        print(f"     Size: {size:,} bytes  |  Segments: {len(segments)}")
        print(f"     Play: vidgenerator/videos/{doc_id}.mp4")
        return 0
    print(f"\nFAIL {err or 'Unknown error'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
