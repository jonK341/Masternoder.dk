"""
Forum camouflage agent — writes useful interpretations, stories, and questions
as rotating community personas (one agent, many voices).
"""
from __future__ import annotations

import json
import os
import random
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TOPICS_PATH = os.path.join(_BASE_DIR, "data", "forum_topics.json")
_PERSONAS_PATH = os.path.join(_BASE_DIR, "data", "forum_personas.json")
_THREADS_PATH = os.path.join(_BASE_DIR, "data", "forum_threads.json")
_ARTICLES_PATH = os.path.join(_BASE_DIR, "data", "forum_articles.json")

# Fallback pools when LLM is unavailable
_FALLBACK_QUESTIONS = [
    "How do compendium points interact with battle stats?",
    "Best way to earn MN2 without grinding casino all day?",
    "Does anyone understand rulebook V12 generator section?",
    "Podcast episode about hello-world docs — worth a listen?",
    "Where do I find calm library mode again?",
]
_FALLBACK_STORIES = [
    "I read page 7 of the compendium last night and it clicked with the Hunters winter wedding arc.",
    "Started a short documentary on the generator and the AI nailed the B-roll timing.",
    "Our crew ran battlegrounds twice — the trophy unlock felt earned, not handed.",
]
_FALLBACK_ANSWERS = [
    "Check the Forum docs tab — it links to game walkthroughs.",
    "Profile → MN2 wallet for deposits; shop for boosts.",
    "Rulebook V9 shop section covers most economy questions.",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: str, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_topics() -> List[dict]:
    return _load_json(_TOPICS_PATH, {"themes": []}).get("themes") or []


def load_personas() -> List[dict]:
    return _load_json(_PERSONAS_PATH, {"personas": []}).get("personas") or []


def load_threads() -> List[dict]:
    return _load_json(_THREADS_PATH, {"threads": []}).get("threads") or []


def save_threads(threads: List[dict]) -> None:
    _save_json(_THREADS_PATH, {"$schema": "masternoder.forum_threads.v1", "threads": threads})


def public_persona(p: dict) -> dict:
    """Strip internal agent fields — camouflage."""
    return {
        "id": p.get("id"),
        "display_name": p.get("display_name"),
        "avatar": p.get("avatar"),
    }


def public_thread(t: dict) -> dict:
    """Thread safe for API — no agent_seeded flag."""
    posts = []
    for post in t.get("posts") or []:
        posts.append({
            "id": post.get("id"),
            "author_name": post.get("author_name"),
            "avatar": post.get("avatar"),
            "body": post.get("body"),
            "kind": post.get("kind"),
            "created_at": post.get("created_at"),
        })
    return {
        "id": t.get("id"),
        "topic_id": t.get("topic_id"),
        "subforum_id": t.get("subforum_id"),
        "theme_title": t.get("theme_title"),
        "subforum_title": t.get("subforum_title"),
        "title": t.get("title"),
        "posts": posts,
        "post_count": len(posts),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
    }


def pick_persona(exclude_ids: Optional[List[str]] = None) -> dict:
    personas = load_personas()
    if not personas:
        return {"id": "anon", "display_name": "CommunityMember", "avatar": "👤", "writing_style": "neutral", "tone": "friendly"}
    pool = [p for p in personas if p.get("id") not in (exclude_ids or [])]
    if not pool:
        pool = personas
    return random.choice(pool)


def _pick_topic_subforum(kind: str = "question") -> Tuple[dict, dict]:
    themes = load_topics()
    if not themes:
        return (
            {"id": "general", "title": "General"},
            {"id": "questions", "title": "Questions", "allows_questions": True},
        )
    theme = random.choice(themes)
    subs = theme.get("subforums") or [{"id": "general", "title": "General"}]
    if kind == "question":
        qsubs = [s for s in subs if s.get("allows_questions")]
        sub = random.choice(qsubs) if qsubs else random.choice(subs)
    else:
        sub = random.choice(subs)
    return theme, sub


def _persona_system_prompt(persona: dict, theme: dict, sub: dict, kind: str) -> str:
    return (
        f"You are writing a forum post as community member '{persona.get('display_name')}'. "
        f"Writing style: {persona.get('writing_style')}. Tone: {persona.get('tone')}. "
        f"Theme: {theme.get('title')} — subforum: {sub.get('title')}. "
        f"Post kind: {kind}. "
        "Write ONLY the post body (80-220 words). No username prefix. "
        "Sound like a real user on this platform (generator, battle, compendium, MN2). "
        "Be useful, specific, and natural — not marketing."
    )


def _generate_with_llm(persona: dict, theme: dict, sub: dict, kind: str, title_hint: str = "") -> Optional[str]:
    try:
        from backend.services.llm_service import chat
        user_msg = f"Write a forum {kind}."
        if title_hint:
            user_msg += f" Thread title: {title_hint}"
        if kind == "question":
            user_msg += " End with a clear question."
        resp = chat(
            [
                {"role": "system", "content": _persona_system_prompt(persona, theme, sub, kind)},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.85,
            max_tokens=400,
            task_type="default",
        )
        if resp.success and resp.content:
            return resp.content.strip()
    except Exception:
        pass
    return None


def _fallback_body(kind: str) -> str:
    if kind == "question":
        return random.choice(_FALLBACK_QUESTIONS)
    if kind == "story":
        return random.choice(_FALLBACK_STORIES)
    return random.choice(_FALLBACK_ANSWERS)


def _generate_title(body: str, kind: str) -> str:
    first_line = (body.split("\n")[0] or "").strip()
    if len(first_line) > 15 and len(first_line) < 120:
        return first_line.rstrip("?") + ("?" if kind == "question" and not first_line.endswith("?") else "")
    prefixes = {"question": "Quick question", "story": "Story time", "answer": "Re:", "interpretation": "My read on"}
    return f"{prefixes.get(kind, 'Discussion')} — {uuid.uuid4().hex[:6]}"


def _make_post(persona: dict, body: str, kind: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "persona_id": persona.get("id"),
        "author_name": persona.get("display_name"),
        "avatar": persona.get("avatar"),
        "body": body,
        "kind": kind,
        "created_at": _iso_now(),
    }


def create_thread(
    topic_id: Optional[str] = None,
    subforum_id: Optional[str] = None,
    kind: str = "question",
    title: Optional[str] = None,
    body: Optional[str] = None,
    author_name: Optional[str] = None,
    agent_authored: bool = False,
) -> dict:
    """Create a thread with opening post."""
    if topic_id and subforum_id:
        theme = next((t for t in load_topics() if t.get("id") == topic_id), None)
        sub = None
        if theme:
            sub = next((s for s in (theme.get("subforums") or []) if s.get("id") == subforum_id), None)
        if not theme or not sub:
            theme, sub = _pick_topic_subforum(kind)
    else:
        theme, sub = _pick_topic_subforum(kind)

    persona = pick_persona() if agent_authored or not author_name else {
        "id": "user",
        "display_name": author_name or "Member",
        "avatar": "👤",
    }

    if not body:
        body = _generate_with_llm(persona, theme, sub, kind) or _fallback_body(kind)
    if not title:
        title = _generate_title(body, kind)

    now = _iso_now()
    thread = {
        "id": str(uuid.uuid4()),
        "topic_id": theme.get("id"),
        "subforum_id": sub.get("id"),
        "theme_title": theme.get("title"),
        "subforum_title": sub.get("title"),
        "title": title[:200],
        "posts": [_make_post(persona, body, kind)],
        "created_at": now,
        "updated_at": now,
        "agent_seeded": agent_authored,
    }
    threads = load_threads()
    threads.insert(0, thread)
    save_threads(threads)
    return thread


def reply_to_thread(
    thread_id: str,
    body: Optional[str] = None,
    kind: str = "answer",
    author_name: Optional[str] = None,
    agent_authored: bool = False,
) -> Optional[dict]:
    threads = load_threads()
    thread = next((t for t in threads if t.get("id") == thread_id), None)
    if not thread:
        return None

    used_personas = [p.get("persona_id") for p in thread.get("posts") or [] if p.get("persona_id")]
    persona = pick_persona(exclude_ids=used_personas if agent_authored else None)
    if not agent_authored and author_name:
        persona = {"id": "user", "display_name": author_name, "avatar": "👤"}

    theme = {"id": thread.get("topic_id"), "title": thread.get("theme_title")}
    sub = {"id": thread.get("subforum_id"), "title": thread.get("subforum_title")}

    if not body:
        body = _generate_with_llm(persona, theme, sub, kind, thread.get("title")) or _fallback_body(kind)

    post = _make_post(persona, body, kind)
    thread.setdefault("posts", []).append(post)
    thread["updated_at"] = _iso_now()
    save_threads(threads)
    return post


def run_agent_cycle(
    max_new_threads: int = 2,
    max_replies: int = 3,
) -> dict:
    """
    One camouflage cycle: new threads + cross-persona replies.
    Looks like different users; one agent orchestrates.
    """
    results = {"threads_created": [], "replies": [], "errors": []}
    kinds = ["question", "story", "interpretation", "question"]

    for i in range(max(0, min(max_new_threads, 5))):
        try:
            kind = kinds[i % len(kinds)]
            t = create_thread(kind=kind, agent_authored=True)
            results["threads_created"].append(t.get("id"))
        except Exception as e:
            results["errors"].append(str(e))

    threads = load_threads()
    # Reply to recent threads (including ones just created)
    candidates = threads[: max_replies + max_new_threads]
    for t in candidates[:max(0, min(max_replies, 8))]:
        try:
            post = reply_to_thread(t.get("id"), agent_authored=True, kind="answer")
            if post:
                results["replies"].append({"thread_id": t.get("id"), "post_id": post.get("id")})
        except Exception as e:
            results["errors"].append(str(e))

    # Mirror one interpretation as a forum article occasionally
    if results["threads_created"] and random.random() < 0.4:
        try:
            _mirror_thread_to_article(threads[0] if threads else None)
            results["article_mirrored"] = True
        except Exception:
            pass

    results["success"] = not results["errors"] or bool(results["threads_created"] or results["replies"])
    return results


def _mirror_thread_to_article(thread: Optional[dict]) -> None:
    if not thread or not thread.get("posts"):
        return
    opening = thread["posts"][0]
    if opening.get("kind") not in ("story", "interpretation"):
        return
    data = _load_json(_ARTICLES_PATH, {"articles": []})
    articles = data.get("articles") or []
    articles.insert(0, {
        "id": str(uuid.uuid4()),
        "slug": f"community-{thread.get('id', '')[:8]}",
        "title": thread.get("title"),
        "author_id": opening.get("persona_id", "community"),
        "author_name": opening.get("author_name"),
        "category": thread.get("topic_id", "community"),
        "featured": False,
        "created_at": _iso_now(),
        "updated_at": _iso_now(),
        "summary": (opening.get("body") or "")[:240],
        "body_markdown": opening.get("body"),
    })
    _save_json(_ARTICLES_PATH, {"articles": articles[:200], "$schema": "masternoder.forum_articles.v1"})


def seed_initial_content() -> dict:
    """Bootstrap forum if empty."""
    if load_threads():
        return {"success": True, "skipped": True, "reason": "threads already exist"}
    out = run_agent_cycle(max_new_threads=4, max_replies=4)
    out["seeded"] = True
    return out
