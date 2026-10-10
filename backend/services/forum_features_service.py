"""
Forum V2 features — personalization, notifications, polls, badges, digests.

Kept separate from forum_agent_service (the posting engine) so the camouflage
agent stays lean. All state is file-backed JSON under data/.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_USER_STATE_PATH = os.path.join(_BASE_DIR, "data", "forum_user_state.json")
_NOTIFS_PATH = os.path.join(_BASE_DIR, "data", "forum_notifications.json")
_POLLS_PATH = os.path.join(_BASE_DIR, "data", "forum_polls.json")


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return json.loads(json.dumps(default))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return json.loads(json.dumps(default))


def _save(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Per-user state: bookmarks, follows, tag follows, read-state, saved searches
# ---------------------------------------------------------------------------
def _user_state_all() -> dict:
    return _load(_USER_STATE_PATH, {"$schema": "masternoder.forum_user_state.v1", "users": {}})


def _user(store: dict, uid: str) -> dict:
    users = store.setdefault("users", {})
    return users.setdefault(uid, {
        "bookmarks": [],
        "follows": [],
        "tag_follows": [],
        "read": {},
        "saved_searches": [],
        "last_seen": None,
        "prefs": {},
    })


def get_user_state(uid: str) -> dict:
    store = _user_state_all()
    u = _user(store, uid)
    return {
        "user_id": uid,
        "bookmarks": u.get("bookmarks", []),
        "follows": u.get("follows", []),
        "tag_follows": u.get("tag_follows", []),
        "saved_searches": u.get("saved_searches", []),
        "read_count": len(u.get("read", {})),
        "prefs": u.get("prefs", {}),
        "last_seen": u.get("last_seen"),
    }


def _toggle_in_list(store: dict, uid: str, field: str, value: str) -> dict:
    u = _user(store, uid)
    lst = u.setdefault(field, [])
    if value in lst:
        lst.remove(value)
        active = False
    else:
        lst.insert(0, value)
        active = True
    return {"field": field, "value": value, "active": active, "count": len(lst)}


def toggle_bookmark(uid: str, thread_id: str) -> dict:
    store = _user_state_all()
    r = _toggle_in_list(store, uid, "bookmarks", thread_id)
    _save(_USER_STATE_PATH, store)
    return {"bookmarked": r["active"], "count": r["count"]}


def toggle_follow(uid: str, thread_id: str) -> dict:
    store = _user_state_all()
    r = _toggle_in_list(store, uid, "follows", thread_id)
    _save(_USER_STATE_PATH, store)
    return {"following": r["active"], "count": r["count"]}


def toggle_tag_follow(uid: str, tag: str) -> dict:
    store = _user_state_all()
    r = _toggle_in_list(store, uid, "tag_follows", (tag or "").lower())
    _save(_USER_STATE_PATH, store)
    return {"following": r["active"], "count": r["count"]}


def thread_followers(thread_id: str) -> List[str]:
    store = _user_state_all()
    return [uid for uid, u in (store.get("users") or {}).items()
            if thread_id in (u.get("follows") or [])]


def mark_read(uid: str, thread_id: str) -> dict:
    store = _user_state_all()
    u = _user(store, uid)
    u.setdefault("read", {})[thread_id] = _iso_now()
    _save(_USER_STATE_PATH, store)
    return {"thread_id": thread_id, "read": True}


def is_read(uid: str, thread_id: str, updated_at: Optional[str]) -> bool:
    store = _user_state_all()
    u = _user(store, uid)
    seen = (u.get("read") or {}).get(thread_id)
    if not seen:
        return False
    if not updated_at:
        return True
    return seen >= updated_at


def read_map(uid: str) -> Dict[str, str]:
    store = _user_state_all()
    return (_user(store, uid).get("read") or {})


def set_pref(uid: str, key: str, value: Any) -> dict:
    store = _user_state_all()
    u = _user(store, uid)
    u.setdefault("prefs", {})[str(key)[:40]] = value
    _save(_USER_STATE_PATH, store)
    return {"prefs": u["prefs"]}


def save_search(uid: str, query: str, filters: Optional[dict] = None) -> dict:
    store = _user_state_all()
    u = _user(store, uid)
    searches = u.setdefault("saved_searches", [])
    entry = {"id": uuid.uuid4().hex[:8], "q": (query or "").strip()[:120],
             "filters": filters or {}, "at": _iso_now()}
    searches.insert(0, entry)
    u["saved_searches"] = searches[:25]
    _save(_USER_STATE_PATH, store)
    return entry


def delete_saved_search(uid: str, search_id: str) -> dict:
    store = _user_state_all()
    u = _user(store, uid)
    before = len(u.get("saved_searches") or [])
    u["saved_searches"] = [s for s in (u.get("saved_searches") or []) if s.get("id") != search_id]
    _save(_USER_STATE_PATH, store)
    return {"removed": before - len(u["saved_searches"])}


def touch_last_seen(uid: str) -> None:
    store = _user_state_all()
    _user(store, uid)["last_seen"] = _iso_now()
    _save(_USER_STATE_PATH, store)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
def _notifs_all() -> dict:
    return _load(_NOTIFS_PATH, {"$schema": "masternoder.forum_notifications.v1", "notifications": {}})


def push_notification(uid: str, ntype: str, *, thread_id: str = "", post_id: str = "",
                      actor: str = "", text: str = "") -> Optional[dict]:
    if not uid:
        return None
    store = _notifs_all()
    inbox = store.setdefault("notifications", {}).setdefault(uid, [])
    entry = {
        "id": uuid.uuid4().hex[:10],
        "type": ntype,
        "thread_id": thread_id,
        "post_id": post_id,
        "actor": actor,
        "text": text[:200],
        "at": _iso_now(),
        "read": False,
    }
    inbox.insert(0, entry)
    store["notifications"][uid] = inbox[:200]
    _save(_NOTIFS_PATH, store)
    return entry


def notify_thread_followers(thread_id: str, *, actor: str, text: str, exclude: str = "",
                            post_id: str = "", ntype: str = "reply") -> int:
    count = 0
    for uid in thread_followers(thread_id):
        if uid == exclude:
            continue
        if push_notification(uid, ntype, thread_id=thread_id, post_id=post_id, actor=actor, text=text):
            count += 1
    return count


def notify_mentions(body: str, thread_id: str, *, actor: str, post_id: str = "") -> List[str]:
    mentioned = extract_mentions(body)
    for uid in mentioned:
        push_notification(uid, "mention", thread_id=thread_id, post_id=post_id,
                          actor=actor, text=f"{actor} mentioned you")
    return mentioned


def list_notifications(uid: str, only_unread: bool = False, limit: int = 50) -> List[dict]:
    store = _notifs_all()
    inbox = (store.get("notifications") or {}).get(uid, [])
    if only_unread:
        inbox = [n for n in inbox if not n.get("read")]
    return inbox[:limit]


def unread_count(uid: str) -> int:
    store = _notifs_all()
    return sum(1 for n in (store.get("notifications") or {}).get(uid, []) if not n.get("read"))


def mark_notifications_read(uid: str, ids: Optional[List[str]] = None) -> dict:
    store = _notifs_all()
    inbox = (store.get("notifications") or {}).get(uid, [])
    n = 0
    for item in inbox:
        if ids is None or item.get("id") in ids:
            if not item.get("read"):
                item["read"] = True
                n += 1
    _save(_NOTIFS_PATH, store)
    return {"marked": n, "unread": unread_count(uid)}


# ---------------------------------------------------------------------------
# Mentions + hashtags
# ---------------------------------------------------------------------------
_MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_\-]{2,40})")
_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_\-]{2,32})")


def extract_mentions(text: str) -> List[str]:
    return list(dict.fromkeys(m.group(1) for m in _MENTION_RE.finditer(text or "")))


def extract_hashtags(text: str) -> List[str]:
    return list(dict.fromkeys(m.group(1).lower() for m in _HASHTAG_RE.finditer(text or "")))


# ---------------------------------------------------------------------------
# Polls
# ---------------------------------------------------------------------------
def _polls_all() -> dict:
    return _load(_POLLS_PATH, {"$schema": "masternoder.forum_polls.v1", "polls": {}})


def create_poll(thread_id: str, question: str, options: List[str], *, closes_in_hours: int = 168) -> Optional[dict]:
    opts = [str(o).strip()[:120] for o in (options or []) if str(o).strip()][:8]
    if len(opts) < 2 or not thread_id:
        return None
    store = _polls_all()
    poll = {
        "thread_id": thread_id,
        "question": (question or "").strip()[:200],
        "options": [{"id": uuid.uuid4().hex[:6], "text": o, "votes": 0} for o in opts],
        "voters": {},
        "created_at": _iso_now(),
        "closes_at": (datetime.now(timezone.utc) + timedelta(hours=max(1, closes_in_hours))).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    store.setdefault("polls", {})[thread_id] = poll
    _save(_POLLS_PATH, store)
    return poll


def get_poll(thread_id: str, uid: str = "") -> Optional[dict]:
    store = _polls_all()
    poll = (store.get("polls") or {}).get(thread_id)
    if not poll:
        return None
    total = sum(o.get("votes", 0) for o in poll.get("options", []))
    closed = poll.get("closes_at", "") < _iso_now()
    return {
        "thread_id": thread_id,
        "question": poll.get("question"),
        "options": [
            {**o, "pct": round(100 * o.get("votes", 0) / total, 1) if total else 0.0}
            for o in poll.get("options", [])
        ],
        "total_votes": total,
        "closed": closed,
        "closes_at": poll.get("closes_at"),
        "your_vote": (poll.get("voters") or {}).get(uid) if uid else None,
    }


def vote_poll(thread_id: str, uid: str, option_id: str) -> Optional[dict]:
    store = _polls_all()
    poll = (store.get("polls") or {}).get(thread_id)
    if not poll:
        return None
    if poll.get("closes_at", "") < _iso_now():
        return {"error": "poll closed"}
    voters = poll.setdefault("voters", {})
    prev = voters.get(uid)
    for o in poll["options"]:
        if o["id"] == prev:
            o["votes"] = max(0, o.get("votes", 0) - 1)
    target = next((o for o in poll["options"] if o["id"] == option_id), None)
    if not target:
        return {"error": "invalid option"}
    target["votes"] = target.get("votes", 0) + 1
    voters[uid] = option_id
    _save(_POLLS_PATH, store)
    return get_poll(thread_id, uid)


def has_poll(thread_id: str) -> bool:
    return thread_id in (_polls_all().get("polls") or {})


# ---------------------------------------------------------------------------
# Badges / achievements (computed from author activity)
# ---------------------------------------------------------------------------
_BADGE_RULES = [
    ("first_post", "🌱", "First Post", lambda s: s["threads"] + s["replies"] >= 1),
    ("conversationalist", "💬", "Conversationalist", lambda s: s["replies"] >= 5),
    ("author", "✍️", "Author", lambda s: s["threads"] >= 3),
    ("prolific", "🖋️", "Prolific", lambda s: s["threads"] >= 10),
    ("helper", "🤝", "Helper", lambda s: s["accepted"] >= 1),
    ("guru", "🧠", "Guru", lambda s: s["accepted"] >= 5),
    ("popular", "🔥", "Popular", lambda s: s["reactions"] >= 10),
    ("celebrated", "🏆", "Celebrated", lambda s: s["reactions"] >= 50),
]


def author_stats(author_name: str, threads: List[dict]) -> dict:
    s = {"threads": 0, "replies": 0, "reactions": 0, "accepted": 0}
    for t in threads:
        for i, p in enumerate(t.get("posts") or []):
            if p.get("author_name") != author_name:
                continue
            if i == 0:
                s["threads"] += 1
            else:
                s["replies"] += 1
            s["reactions"] += sum((p.get("reactions") or {}).values())
            if p.get("is_accepted"):
                s["accepted"] += 1
    return s


def compute_badges(author_name: str, threads: List[dict]) -> List[dict]:
    s = author_stats(author_name, threads)
    return [
        {"id": bid, "icon": icon, "label": label}
        for bid, icon, label, rule in _BADGE_RULES if rule(s)
    ]


def reputation_level(reputation: int) -> dict:
    tiers = [
        (0, "Newcomer", "🟢"), (50, "Regular", "🔵"), (150, "Trusted", "🟣"),
        (400, "Veteran", "🟠"), (1000, "Legend", "🔴"),
    ]
    level = tiers[0]
    for t in tiers:
        if reputation >= t[0]:
            level = t
    idx = tiers.index(level)
    nxt = tiers[idx + 1] if idx + 1 < len(tiers) else None
    return {
        "level": level[1], "icon": level[2], "min": level[0],
        "next": nxt[1] if nxt else None,
        "next_at": nxt[0] if nxt else None,
        "progress": round(100 * (reputation - level[0]) / (nxt[0] - level[0]), 1) if nxt else 100.0,
    }
