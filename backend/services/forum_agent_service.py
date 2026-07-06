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
        "bio": p.get("bio"),
        "badge": p.get("badge"),
        "reputation": persona_reputation(p.get("id")),
    }


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s or "thread")[:60]


def _normalize_thread(t: dict) -> dict:
    """Backfill new schema fields on threads created before the upgrade."""
    t.setdefault("tags", [])
    t.setdefault("kind", (t.get("posts") or [{}])[0].get("kind", "question"))
    t.setdefault("views", 0)
    t.setdefault("votes", 0)
    t.setdefault("voters", [])
    t.setdefault("downvoters", [])
    t.setdefault("pinned", False)
    t.setdefault("locked", False)
    t.setdefault("solved", False)
    t.setdefault("deleted", False)
    t.setdefault("accepted_post_id", None)
    if not t.get("slug"):
        t["slug"] = _slugify(t.get("title") or "")
    for post in t.get("posts") or []:
        post.setdefault("edited_at", None)
        post.setdefault("edit_count", 0)
        post.setdefault("history", [])
        post.setdefault("deleted", False)
        post.setdefault("is_accepted", False)
        r = post.get("reactions")
        if not isinstance(r, dict):
            post["reactions"] = _empty_reactions()
        else:
            for k in REACTION_KEYS:
                r.setdefault(k, 0)
    return t


def word_count(text: str) -> int:
    return len((text or "").split())


def reading_time_min(text: str) -> int:
    return max(1, round(word_count(text) / 200.0))


def thread_score(t: dict) -> float:
    """Hotness score — votes, reactions, replies decayed by age."""
    votes = t.get("votes", 0) or 0
    reacts = sum(
        sum((p.get("reactions") or {}).values()) for p in (t.get("posts") or [])
    )
    replies = max(0, len(t.get("posts") or []) - 1)
    views = t.get("views", 0) or 0
    base = votes * 4 + reacts * 2 + replies * 3 + views * 0.2
    # Recency boost
    try:
        updated = datetime.fromisoformat((t.get("updated_at") or "").replace("Z", "+00:00"))
        age_h = max(1.0, (datetime.now(timezone.utc) - updated).total_seconds() / 3600.0)
    except Exception:
        age_h = 48.0
    return base / (age_h ** 0.35)


def public_thread(t: dict, *, detail: bool = True, float_accepted: bool = False) -> dict:
    """Thread safe for API — no agent_seeded flag."""
    t = _normalize_thread(t)
    posts = []
    for post in t.get("posts") or []:
        deleted = bool(post.get("deleted"))
        posts.append({
            "id": post.get("id"),
            "author_name": post.get("author_name"),
            "avatar": post.get("avatar"),
            "body": "[deleted]" if deleted else post.get("body"),
            "kind": post.get("kind"),
            "created_at": post.get("created_at"),
            "edited_at": post.get("edited_at"),
            "edit_count": post.get("edit_count", 0),
            "deleted": deleted,
            "reactions": post.get("reactions") or _empty_reactions(),
            "reaction_total": sum((post.get("reactions") or {}).values()),
            "is_accepted": bool(post.get("is_accepted")),
            "word_count": word_count(post.get("body") or ""),
        })
    if float_accepted and len(posts) > 1:
        head, tail = posts[0], posts[1:]
        tail.sort(key=lambda p: (not p.get("is_accepted"), p.get("created_at") or ""))
        posts = [head] + tail
    op_body = ((t.get("posts") or [{}])[0].get("body")) or ""
    out = {
        "id": t.get("id"),
        "slug": t.get("slug") or _slugify(t.get("title") or ""),
        "topic_id": t.get("topic_id"),
        "subforum_id": t.get("subforum_id"),
        "theme_title": t.get("theme_title"),
        "subforum_title": t.get("subforum_title"),
        "title": t.get("title"),
        "kind": t.get("kind"),
        "tags": t.get("tags") or [],
        "post_count": len(posts),
        "reply_count": max(0, len(posts) - 1),
        "views": t.get("views", 0),
        "votes": t.get("votes", 0),
        "downvotes": len(t.get("downvoters") or []),
        "net_votes": (t.get("votes", 0) or 0) - len(t.get("downvoters") or []),
        "pinned": bool(t.get("pinned")),
        "locked": bool(t.get("locked")),
        "solved": bool(t.get("solved")),
        "deleted": bool(t.get("deleted")),
        "accepted_post_id": t.get("accepted_post_id"),
        "score": round(thread_score(t), 2),
        "word_count": word_count(op_body),
        "reading_time_min": reading_time_min(op_body),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
    }
    if detail:
        out["posts"] = posts
    else:
        op = posts[0] if posts else {}
        out["excerpt"] = (op.get("body") or "")[:200]
        out["author_name"] = op.get("author_name")
        out["avatar"] = op.get("avatar")
    return out


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


REACTION_KEYS = ("like", "helpful", "insightful", "celebrate")


def _empty_reactions() -> Dict[str, int]:
    return {k: 0 for k in REACTION_KEYS}


def _make_post(persona: dict, body: str, kind: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "persona_id": persona.get("id"),
        "author_name": persona.get("display_name"),
        "avatar": persona.get("avatar"),
        "body": body,
        "kind": kind,
        "created_at": _iso_now(),
        "edited_at": None,
        "reactions": _empty_reactions(),
        "is_accepted": False,
    }


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
_TAG_KEYWORDS = {
    "mn2": "mn2",
    "staking": "staking",
    "stake": "staking",
    "reward": "rewards",
    "battle": "battle",
    "generator": "generator",
    "compendium": "compendium",
    "rulebook": "rulebooks",
    "podcast": "podcast",
    "casino": "casino",
    "wallet": "wallet",
    "economy": "economy",
    "guide": "guides",
    "walkthrough": "guides",
    "story": "lore",
    "lore": "lore",
    "paragraph": "paragraphs",
    "support": "support",
    "bug": "bugs",
    "video": "video",
    "gallery": "gallery",
}


def suggest_tags(text: str, limit: int = 4) -> List[str]:
    """Derive lightweight tags from post text (camouflage-friendly)."""
    low = (text or "").lower()
    found: List[str] = []
    for kw, tag in _TAG_KEYWORDS.items():
        if kw in low and tag not in found:
            found.append(tag)
        if len(found) >= limit:
            break
    return found


def create_thread(
    topic_id: Optional[str] = None,
    subforum_id: Optional[str] = None,
    kind: str = "question",
    title: Optional[str] = None,
    body: Optional[str] = None,
    author_name: Optional[str] = None,
    agent_authored: bool = False,
    tags: Optional[List[str]] = None,
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

    if tags is None:
        tags = suggest_tags(f"{title} {body}")

    now = _iso_now()
    thread = {
        "id": str(uuid.uuid4()),
        "topic_id": theme.get("id"),
        "subforum_id": sub.get("id"),
        "theme_title": theme.get("title"),
        "subforum_title": sub.get("title"),
        "title": title[:200],
        "slug": _slugify(title[:200]),
        "kind": kind,
        "tags": tags[:6],
        "posts": [_make_post(persona, body, kind)],
        "created_at": now,
        "updated_at": now,
        "views": 0,
        "votes": 0,
        "voters": [],
        "downvoters": [],
        "pinned": False,
        "locked": False,
        "solved": False,
        "deleted": False,
        "accepted_post_id": None,
        "agent_seeded": agent_authored,
    }
    threads = load_threads()
    threads.insert(0, thread)
    save_threads(threads)
    return thread


class ThreadLockedError(Exception):
    """Raised when replying to a locked thread."""


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
    if thread.get("locked"):
        raise ThreadLockedError("thread is locked")

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


# ---------------------------------------------------------------------------
# Interaction engine — views, votes, reactions, accept, pin, lock, edit
# ---------------------------------------------------------------------------
def _mutate_thread(thread_id: str, fn):
    threads = load_threads()
    for i, t in enumerate(threads):
        if t.get("id") == thread_id:
            threads[i] = _normalize_thread(t)
            result = fn(threads[i])
            save_threads(threads)
            return result
    return None


def register_view(thread_id: str) -> Optional[int]:
    def _fn(t):
        t["views"] = (t.get("views", 0) or 0) + 1
        return t["views"]
    return _mutate_thread(thread_id, _fn)


def vote_thread(thread_id: str, voter: str, direction: int = 1) -> Optional[dict]:
    """Up/down vote a thread. One up + one down slot per voter; re-voting toggles.

    direction > 0 = upvote, direction < 0 = downvote, direction 0 = clear.
    """
    def _fn(t):
        up = t.setdefault("voters", [])
        down = t.setdefault("downvoters", [])
        vid = str(voter or "anon")
        if direction > 0:
            if vid not in up:
                up.append(vid)
            if vid in down:
                down.remove(vid)
        elif direction < 0:
            if vid not in down:
                down.append(vid)
            if vid in up:
                up.remove(vid)
        else:
            if vid in up:
                up.remove(vid)
            if vid in down:
                down.remove(vid)
        t["votes"] = len(up)
        state = 1 if vid in up else (-1 if vid in down else 0)
        return {
            "votes": len(up),
            "downvotes": len(down),
            "net_votes": len(up) - len(down),
            "voted": vid in up,
            "vote_state": state,
        }
    return _mutate_thread(thread_id, _fn)


def react_to_post(thread_id: str, post_id: str, reaction: str) -> Optional[dict]:
    reaction = (reaction or "").lower()
    if reaction not in REACTION_KEYS:
        return None

    def _fn(t):
        for p in t.get("posts") or []:
            if p.get("id") == post_id:
                r = p.setdefault("reactions", _empty_reactions())
                r[reaction] = (r.get(reaction, 0) or 0) + 1
                return {"post_id": post_id, "reactions": r}
        return None
    return _mutate_thread(thread_id, _fn)


def accept_answer(thread_id: str, post_id: str) -> Optional[dict]:
    def _fn(t):
        found = False
        for p in t.get("posts") or []:
            is_it = p.get("id") == post_id
            p["is_accepted"] = is_it
            found = found or is_it
        if not found:
            return None
        t["accepted_post_id"] = post_id
        t["solved"] = True
        return {"solved": True, "accepted_post_id": post_id}
    return _mutate_thread(thread_id, _fn)


def set_pinned(thread_id: str, pinned: bool = True) -> Optional[dict]:
    return _mutate_thread(thread_id, lambda t: t.update({"pinned": bool(pinned)}) or {"pinned": bool(pinned)})


def set_locked(thread_id: str, locked: bool = True) -> Optional[dict]:
    return _mutate_thread(thread_id, lambda t: t.update({"locked": bool(locked)}) or {"locked": bool(locked)})


def edit_post(thread_id: str, post_id: str, new_body: str) -> Optional[dict]:
    def _fn(t):
        for p in t.get("posts") or []:
            if p.get("id") == post_id:
                hist = p.setdefault("history", [])
                hist.append({"body": p.get("body"), "at": p.get("edited_at") or p.get("created_at")})
                p["history"] = hist[-10:]
                p["body"] = (new_body or "").strip()[:50000]
                p["edited_at"] = _iso_now()
                p["edit_count"] = (p.get("edit_count", 0) or 0) + 1
                t["updated_at"] = _iso_now()
                return {"post_id": post_id, "edited_at": p["edited_at"], "edit_count": p["edit_count"]}
        return None
    return _mutate_thread(thread_id, _fn)


def post_history(thread_id: str, post_id: str) -> Optional[List[dict]]:
    for t in load_threads():
        if t.get("id") == thread_id:
            for p in t.get("posts") or []:
                if p.get("id") == post_id:
                    return p.get("history") or []
    return None


def delete_thread(thread_id: str, deleted: bool = True) -> Optional[dict]:
    return _mutate_thread(thread_id, lambda t: t.update({"deleted": bool(deleted)}) or {"deleted": bool(deleted)})


def delete_post(thread_id: str, post_id: str, deleted: bool = True) -> Optional[dict]:
    def _fn(t):
        for p in t.get("posts") or []:
            if p.get("id") == post_id:
                p["deleted"] = bool(deleted)
                return {"post_id": post_id, "deleted": bool(deleted)}
        return None
    return _mutate_thread(thread_id, _fn)


def set_thread_tags(thread_id: str, tags: List[str]) -> Optional[dict]:
    clean = [str(x).strip().lower()[:24] for x in (tags or []) if str(x).strip()][:6]
    return _mutate_thread(thread_id, lambda t: t.update({"tags": clean}) or {"tags": clean})


# ---------------------------------------------------------------------------
# Duplicate detection + per-tag reputation
# ---------------------------------------------------------------------------
def _title_tokens(title: str) -> set:
    return set(re.findall(r"[a-z0-9]{3,}", (title or "").lower()))


def similar_threads(title: str, *, exclude_id: str = "", limit: int = 5, min_overlap: float = 0.35) -> List[dict]:
    """Find threads with similar titles (Jaccard on word tokens) — dedupe helper."""
    base = _title_tokens(title)
    if not base:
        return []
    out = []
    for t in load_threads():
        if t.get("id") == exclude_id or t.get("deleted"):
            continue
        toks = _title_tokens(t.get("title") or "")
        if not toks:
            continue
        sim = len(base & toks) / len(base | toks)
        if sim >= min_overlap:
            out.append((sim, _normalize_thread(t)))
    out.sort(key=lambda x: x[0], reverse=True)
    return [{"similarity": round(s, 2), **public_thread(t, detail=False)} for s, t in out[:limit]]


def tag_reputation(author_name: str) -> Dict[str, int]:
    """Reputation broken down per tag for an author."""
    per_tag: Dict[str, int] = {}
    for t in load_threads():
        tags = t.get("tags") or []
        for i, p in enumerate(t.get("posts") or []):
            if p.get("author_name") != author_name:
                continue
            pts = (10 if i == 0 else 5) + sum((p.get("reactions") or {}).values()) * 2
            if p.get("is_accepted"):
                pts += 25
            for tag in tags:
                per_tag[tag] = per_tag.get(tag, 0) + pts
    return dict(sorted(per_tag.items(), key=lambda x: x[1], reverse=True))


# ---------------------------------------------------------------------------
# Discovery — search, tags, trending, related, stats, leaderboard
# ---------------------------------------------------------------------------
def list_threads_sorted(
    topic_id: str = "",
    subforum_id: str = "",
    tag: str = "",
    kind: str = "",
    sort: str = "new",
    query: str = "",
    offset: int = 0,
    limit: int = 20,
    ids: Optional[List[str]] = None,
    include_deleted: bool = False,
) -> Tuple[List[dict], int]:
    threads = [_normalize_thread(t) for t in load_threads()]
    if not include_deleted:
        threads = [t for t in threads if not t.get("deleted")]
    if ids is not None:
        idset = set(ids)
        threads = [t for t in threads if t.get("id") in idset]
    if topic_id:
        threads = [t for t in threads if t.get("topic_id") == topic_id]
    if subforum_id:
        threads = [t for t in threads if t.get("subforum_id") == subforum_id]
    if tag:
        threads = [t for t in threads if tag.lower() in [x.lower() for x in (t.get("tags") or [])]]
    if kind:
        threads = [t for t in threads if t.get("kind") == kind]
    if query:
        q = query.lower()
        threads = [
            t for t in threads
            if q in (t.get("title") or "").lower()
            or any(q in (p.get("body") or "").lower() for p in (t.get("posts") or []))
            or any(q in tg.lower() for tg in (t.get("tags") or []))
        ]

    if sort == "top":
        threads.sort(key=lambda t: t.get("votes", 0), reverse=True)
    elif sort == "hot":
        threads.sort(key=thread_score, reverse=True)
    elif sort == "active":
        threads.sort(key=lambda t: len(t.get("posts") or []), reverse=True)
    elif sort == "unanswered":
        threads = [t for t in threads if len(t.get("posts") or []) <= 1]
        threads.sort(key=lambda t: t.get("created_at") or "", reverse=True)
    elif sort == "views":
        threads.sort(key=lambda t: t.get("views", 0), reverse=True)
    elif sort == "solved":
        threads = [t for t in threads if t.get("solved")]
        threads.sort(key=lambda t: t.get("updated_at") or "", reverse=True)
    elif sort == "unsolved":
        threads = [t for t in threads if t.get("kind") == "question" and not t.get("solved")]
        threads.sort(key=lambda t: t.get("created_at") or "", reverse=True)
    elif sort == "oldest":
        threads.sort(key=lambda t: t.get("created_at") or "")
    else:  # new
        threads.sort(key=lambda t: t.get("updated_at") or "", reverse=True)

    # Pinned always float to top (except in explicit sort views that override)
    threads.sort(key=lambda t: 0 if t.get("pinned") else 1)

    total = len(threads)
    if limit and limit > 0:
        threads = threads[offset:offset + limit]
    return threads, total


def tag_cloud() -> List[dict]:
    counts: Dict[str, int] = {}
    for t in load_threads():
        for tg in t.get("tags") or []:
            counts[tg] = counts.get(tg, 0) + 1
    return sorted(
        [{"tag": k, "count": v} for k, v in counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )


def trending_threads(limit: int = 5) -> List[dict]:
    threads = [_normalize_thread(t) for t in load_threads()]
    threads.sort(key=thread_score, reverse=True)
    return threads[:limit]


def related_threads(thread_id: str, limit: int = 4) -> List[dict]:
    threads = [_normalize_thread(t) for t in load_threads()]
    base = next((t for t in threads if t.get("id") == thread_id), None)
    if not base:
        return []
    base_tags = set(t.lower() for t in base.get("tags") or [])
    scored = []
    for t in threads:
        if t.get("id") == thread_id:
            continue
        shared = len(base_tags & set(x.lower() for x in t.get("tags") or []))
        same_topic = 1 if t.get("topic_id") == base.get("topic_id") else 0
        rank = shared * 2 + same_topic
        if rank > 0:
            scored.append((rank, t))
    scored.sort(key=lambda x: (x[0], x[1].get("updated_at") or ""), reverse=True)
    return [t for _, t in scored[:limit]]


def forum_stats() -> dict:
    threads = load_threads()
    posts = sum(len(t.get("posts") or []) for t in threads)
    solved = sum(1 for t in threads if t.get("solved"))
    questions = sum(1 for t in threads if t.get("kind") == "question")
    contributors = set()
    for t in threads:
        for p in t.get("posts") or []:
            contributors.add(p.get("author_name"))
    return {
        "threads": len(threads),
        "posts": posts,
        "replies": max(0, posts - len(threads)),
        "solved": solved,
        "questions": questions,
        "solved_rate": round(solved / questions, 3) if questions else 0.0,
        "contributors": len(contributors),
        "tags": len(tag_cloud()),
        "personas": len(load_personas()),
    }


def persona_reputation(persona_id: Optional[str]) -> int:
    """Reputation from posts authored, replies, accepted answers, reactions."""
    if not persona_id:
        return 0
    rep = 0
    for t in load_threads():
        for i, p in enumerate(t.get("posts") or []):
            if p.get("persona_id") != persona_id:
                continue
            rep += 10 if i == 0 else 5
            rep += sum((p.get("reactions") or {}).values()) * 2
            if p.get("is_accepted"):
                rep += 25
    return rep


def leaderboard(limit: int = 10) -> List[dict]:
    tally: Dict[str, dict] = {}
    for t in load_threads():
        for i, p in enumerate(t.get("posts") or []):
            key = p.get("author_name") or "anon"
            row = tally.setdefault(key, {
                "author_name": key,
                "avatar": p.get("avatar"),
                "threads": 0,
                "replies": 0,
                "reactions": 0,
                "accepted": 0,
            })
            if i == 0:
                row["threads"] += 1
            else:
                row["replies"] += 1
            row["reactions"] += sum((p.get("reactions") or {}).values())
            if p.get("is_accepted"):
                row["accepted"] += 1
    for row in tally.values():
        row["reputation"] = (
            row["threads"] * 10 + row["replies"] * 5
            + row["reactions"] * 2 + row["accepted"] * 25
        )
    ranked = sorted(tally.values(), key=lambda r: r["reputation"], reverse=True)
    return ranked[:limit]


def threads_by_author(author_name: str, limit: int = 20) -> List[dict]:
    out = []
    for t in load_threads():
        posts = t.get("posts") or []
        if posts and posts[0].get("author_name") == author_name:
            out.append(_normalize_thread(t))
    return out[:limit]


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

    # Simulate organic engagement — votes, reactions, occasional accepted answer.
    try:
        results["engagement"] = _simulate_engagement(candidates)
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


def _simulate_engagement(candidate_threads: List[dict]) -> dict:
    """Give recent threads believable votes/reactions so the forum looks alive."""
    summary = {"votes": 0, "reactions": 0, "accepted": 0}
    for t in candidate_threads:
        tid = t.get("id")
        if not tid:
            continue
        # A few phantom voters
        for n in range(random.randint(0, 4)):
            vote_thread(tid, voter=f"sim_{uuid.uuid4().hex[:8]}", direction=1)
            summary["votes"] += 1
        # Reactions on replies
        fresh = next((x for x in load_threads() if x.get("id") == tid), None)
        if not fresh:
            continue
        posts = fresh.get("posts") or []
        for p in posts[1:]:
            if random.random() < 0.6:
                react_to_post(tid, p.get("id"), random.choice(REACTION_KEYS))
                summary["reactions"] += 1
        # Occasionally accept an answer for question threads
        if fresh.get("kind") == "question" and len(posts) > 1 and random.random() < 0.35:
            accept_answer(tid, posts[-1].get("id"))
            summary["accepted"] += 1
    return summary


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
