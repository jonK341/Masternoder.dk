"""
Opt-in weekly casino email digest — big wins + Invite Party referral progress.

Uses SMTP via purchase_notification_service._send_email and user email resolution
from monetization_email_service. Prefs live on casino social preferences.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PREFS_DIR = os.path.join(_BASE, "logs", "casino_social_prefs")
_SENT_LOG = os.path.join(_BASE, "logs", "casino_social", "win_digest_sent.jsonl")
_STATE_PATH = os.path.join(_BASE, "logs", "casino_social", "win_digest_state.json")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso_week() -> str:
    return _utcnow().strftime("%G-W%V")


def _load_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _append_log(row: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_SENT_LOG), exist_ok=True)
    with _LOCK:
        with open(_SENT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _iter_opted_in_prefs() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not os.path.isdir(_PREFS_DIR):
        return rows
    for name in os.listdir(_PREFS_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(_PREFS_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if not data.get("email_win_digest"):
            continue
        uid = (data.get("user_id") or "").strip()
        if uid:
            rows.append(data)
    return rows


def build_digest_body(user_id: str) -> Dict[str, Any]:
    """Assemble digest content for one user (email body + metadata)."""
    from backend.services import casino_service
    from backend.services import casino_social_service

    hof = casino_service.get_big_win_hall_of_fame(days=7, limit=8) or {}
    wins = hof.get("wins") or hof.get("entries") or hof.get("hall") or []
    if not isinstance(wins, list):
        wins = []
    quests = casino_social_service.get_referral_quests(user_id) or {}
    invite = casino_social_service.get_referral_invite(user_id) or {}
    party = invite.get("party") or {}
    level = party.get("level") or {}

    win_lines: List[str] = []
    for w in wins[:8]:
        if not isinstance(w, dict):
            continue
        game = w.get("game") or w.get("game_id") or "casino"
        net = w.get("net") or w.get("amount") or w.get("payout") or 0
        cur = w.get("currency") or "coins"
        who = w.get("display") or w.get("handle") or "Player"
        win_lines.append(f"• {who} — {net} {cur} on {game}")

    if not win_lines:
        win_lines.append("• No public big wins this week yet — be the first.")

    quest_lines: List[str] = []
    for q in (quests.get("referrals") or quests.get("quests") or quests.get("rows") or [])[:6]:
        if not isinstance(q, dict):
            continue
        title = q.get("display") or q.get("title") or q.get("referred_user_id") or "guest"
        bets = q.get("bet_count")
        tiers = q.get("tiers") or []
        done_tiers = sum(1 for t in tiers if isinstance(t, dict) and t.get("completed"))
        mark = "✓" if done_tiers else "·"
        extra = f" — {bets} plays, {done_tiers} tiers" if bets is not None else ""
        quest_lines.append(f"{mark} {title}{extra}")
    party_level = quests.get("party") or {}
    if isinstance(party_level, dict) and party_level.get("level"):
        quest_lines.insert(0, f"· Party level: {party_level.get('level')}")
    if not quest_lines:
        quest_lines.append("· Invite friends via /r/ for free practice coins")

    invites = invite.get("successful_invites") or 0
    code = invite.get("referral_code") or ""
    invite_url = invite.get("invite_url") or "https://masternoder.dk/r/"
    level_name = (level.get("current") or {}).get("name") if isinstance(level.get("current"), dict) else level.get("name")
    level_label = level_name or level.get("id") or "Starter"

    subject = "Your MasterNoder Casino weekly digest"
    body = (
        f"MasterNoder2 Casino — weekly digest\n"
        f"{'=' * 40}\n\n"
        f"Lounge highlights (7 days)\n"
        + "\n".join(win_lines)
        + "\n\n"
        f"Your Invite Party\n"
        f"• Code: {code}\n"
        f"• Successful invites: {invites}\n"
        f"• Party level: {level_label}\n"
        f"• Share: {invite_url}\n\n"
        f"Referral quests\n"
        + "\n".join(quest_lines)
        + "\n\n"
        f"Play: https://masternoder.dk/casino/\n"
        f"Ads lander: https://masternoder.dk/casino/go/\n\n"
        f"Unsubscribe: Casino → Social → uncheck “Weekly email digest”.\n"
        f"Play responsibly. 18+ where required.\n"
    )
    return {
        "subject": subject,
        "body": body,
        "invites": invites,
        "win_count": len([w for w in wins if isinstance(w, dict)]),
        "quest_count": len(quest_lines),
    }


def send_digest_for_user(user_id: str, *, force: bool = False) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}

    from backend.services import casino_social_service
    from backend.services.monetization_email_service import resolve_user_email
    from backend.services.purchase_notification_service import _send_email

    prefs = casino_social_service.get_preferences(uid)
    if not prefs.get("email_win_digest") and not force:
        return {"success": True, "skipped": True, "reason": "not_opted_in", "user_id": uid}

    email = (prefs.get("digest_email") or "").strip() or resolve_user_email(uid)
    if not email or "@" not in email:
        return {"success": True, "skipped": True, "reason": "no_email", "user_id": uid}

    week = _iso_week()
    with _LOCK:
        state = _load_json(_STATE_PATH, {})
        user_state = state.setdefault(uid, {})
        if not force and user_state.get("last_week") == week:
            return {"success": True, "skipped": True, "reason": "already_sent", "user_id": uid, "week": week}

    payload = build_digest_body(uid)
    sent = bool(_send_email(payload["subject"], payload["body"], email))
    row = {
        "user_id": uid,
        "email": email,
        "week": week,
        "sent": sent,
        "at": _utcnow().isoformat().replace("+00:00", "Z"),
        "win_count": payload.get("win_count"),
        "invites": payload.get("invites"),
    }
    _append_log(row)
    if sent:
        with _LOCK:
            state = _load_json(_STATE_PATH, {})
            state.setdefault(uid, {})["last_week"] = week
            state[uid]["last_sent_at"] = row["at"]
            _save_json(_STATE_PATH, state)
        try:
            from backend.services.user_engagement import add_notification

            add_notification(
                uid,
                "Weekly casino digest sent",
                "Check your email for lounge wins + Invite Party progress.",
                category="casino_digest",
            )
        except Exception:
            pass
    return {"success": True, "sent": sent, "user_id": uid, "week": week, "email": email}


def run_weekly_win_digest(*, force: bool = False) -> Dict[str, Any]:
    """Ops/cron: email every user with email_win_digest opt-in."""
    opted = _iter_opted_in_prefs()
    sent = skipped = errors = 0
    results: List[Dict[str, Any]] = []
    for prefs in opted:
        uid = prefs.get("user_id") or ""
        try:
            out = send_digest_for_user(uid, force=force)
            results.append(out)
            if out.get("sent"):
                sent += 1
            elif out.get("skipped"):
                skipped += 1
            else:
                errors += 1
        except Exception as exc:
            errors += 1
            results.append({"user_id": uid, "success": False, "error": str(exc)})
    return {
        "success": True,
        "force": force,
        "opted_in": len(opted),
        "sent": sent,
        "skipped": skipped,
        "errors": errors,
        "week": _iso_week(),
        "results": results[:50],
    }
