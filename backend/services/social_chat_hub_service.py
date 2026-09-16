"""Unified social chat hub — cross-network monitor + embeddable portal."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "social_chat_hub_config.json")
_MSG_PATH = os.path.join(_BASE, "logs", "social_chat_hub", "messages.json")
_CROSS_LOG = os.path.join(_BASE, "logs", "social_chat_hub", "cross_posts.jsonl")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_hub_messages() -> List[Dict[str, Any]]:
    if not os.path.isfile(_MSG_PATH):
        return []
    try:
        with open(_MSG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        msgs = data.get("messages") if isinstance(data, dict) else data
        return [m for m in (msgs or []) if isinstance(m, dict)]
    except Exception:
        return []


def _save_hub_messages(messages: List[Dict[str, Any]]) -> None:
    cfg = _load_config()
    cap = int(cfg.get("max_messages") or 1000)
    os.makedirs(os.path.dirname(_MSG_PATH), exist_ok=True)
    trimmed = messages[-cap:]
    tmp = _MSG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"messages": trimmed, "updated_at": _utcnow_iso()}, f, indent=2)
    os.replace(tmp, _MSG_PATH)


def _profile_identity(user_id: str) -> Dict[str, Any]:
    try:
        from backend.routes.social_routes import _profile_identity as social_identity
        return social_identity(user_id)
    except Exception:
        return {"display_name": user_id or "Player", "avatar": None}


def _append_cross_log(row: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_CROSS_LOG), exist_ok=True)
    with open(_CROSS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _legacy_social_messages(limit: int) -> List[Dict[str, Any]]:
    try:
        from backend.routes.social_routes import _load_social
        social = _load_social()
        out: List[Dict[str, Any]] = []
        for m in (social.get("chat_messages") or [])[-limit:]:
            if not isinstance(m, dict):
                continue
            out.append({
                **m,
                "source": "legacy_social",
                "networks": m.get("networks") or ["site"],
                "fx": m.get("fx") or "none",
            })
        return out
    except Exception:
        return []


def get_hub_config() -> Dict[str, Any]:
    cfg = _load_config()
    share_networks = []
    try:
        path = os.path.join(_BASE, "data", "social_networks.json")
        with open(path, "r", encoding="utf-8") as f:
            sn = json.load(f)
        share_networks = sn.get("networks") or []
    except Exception:
        pass
    return {
        "success": True,
        "room_id": cfg.get("room_id") or "unified_social",
        "tagline": cfg.get("tagline"),
        "networks": cfg.get("networks") or [],
        "fx_effects": cfg.get("fx_effects") or [],
        "default_cross_networks": cfg.get("default_cross_networks") or ["site"],
        "share_networks": share_networks,
        "portal_href": "/chat/",
    }


def get_unified_feed(*, limit: int = 80, network: Optional[str] = None) -> Dict[str, Any]:
    limit = min(200, max(1, int(limit or 80)))
    hub_msgs = _load_hub_messages()
    legacy = _legacy_social_messages(limit)
    merged: Dict[str, Dict[str, Any]] = {}
    for m in legacy + hub_msgs:
        mid = str(m.get("id") or uuid.uuid4())
        merged[mid] = m
    rows = sorted(merged.values(), key=lambda x: x.get("created_at") or "")
    if network:
        net = network.strip().lower()
        rows = [r for r in rows if net in [n.lower() for n in (r.get("networks") or ["site"])]]
    rows = rows[-limit:]
    for row in rows:
        if not row.get("display_name"):
            ident = _profile_identity(row.get("user_id") or "")
            row["display_name"] = ident.get("display_name")
            row["avatar"] = ident.get("avatar")
    nets = _load_config().get("networks") or []
    return {
        "success": True,
        "messages": rows,
        "count": len(rows),
        "networks": nets,
        "room_id": _load_config().get("room_id"),
    }


def get_monitor() -> Dict[str, Any]:
    cfg = get_hub_config()
    feed = get_unified_feed(limit=50)
    by_net: Dict[str, int] = {}
    for m in feed.get("messages") or []:
        for n in m.get("networks") or ["site"]:
            by_net[n] = by_net.get(n, 0) + 1
    return {
        "success": True,
        "generated_at": _utcnow_iso(),
        "config": cfg,
        "totals": {
            "messages": len(_load_hub_messages()) + len(_legacy_social_messages(9999)),
            "hub_stored": len(_load_hub_messages()),
            "by_network": by_net,
        },
        "recent": feed.get("messages") or [],
    }


def cross_send(
    user_id: str,
    message: str,
    *,
    networks: Optional[List[str]] = None,
    fx: str = "none",
    source_site: Optional[str] = None,
    ai_reply: bool = False,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    text = (message or "").strip()
    if not text:
        return {"success": False, "error": "message_required"}
    text = text[:1000]
    cfg = _load_config()
    allowed = {n.get("id") for n in (cfg.get("networks") or []) if n.get("id")}
    targets = [n for n in (networks or cfg.get("default_cross_networks") or ["site"]) if n in allowed]
    if not targets:
        targets = ["site"]
    fx_id = (fx or "none").strip()
    fx_ok = {e.get("id") for e in (cfg.get("fx_effects") or [])}
    if fx_id not in fx_ok:
        fx_id = "none"
    identity = _profile_identity(uid)
    msg_id = "hub_" + str(uuid.uuid4())[:12]
    row = {
        "id": msg_id,
        "user_id": uid,
        "display_name": identity.get("display_name"),
        "avatar": identity.get("avatar"),
        "message": text,
        "created_at": _utcnow_iso(),
        "room": cfg.get("room_id") or "unified_social",
        "networks": targets,
        "fx": fx_id,
        "source_site": source_site or "portal",
        "cross_post": True,
    }
    msgs = _load_hub_messages()
    msgs.append(row)
    _save_hub_messages(msgs)
    _append_cross_log({"id": msg_id, "user_id": uid, "networks": targets, "fx": fx_id, "at": row["created_at"]})
    try:
        from backend.routes.social_routes import _load_social, _save_social, push_activity
        social = _load_social()
        legacy = {
            "id": msg_id,
            "user_id": uid,
            "display_name": identity.get("display_name"),
            "avatar": identity.get("avatar"),
            "message": text,
            "created_at": row["created_at"],
            "room": "social",
            "networks": targets,
            "fx": fx_id,
        }
        chat_messages = social.setdefault("chat_messages", [])
        chat_messages.append(legacy)
        cap = int(social.get("max_chat_messages") or 500)
        social["chat_messages"] = chat_messages[-cap:]
        _save_social(social)
        push_activity(uid, "social_chat", "Cross-posted to " + ", ".join(targets), {"message_id": msg_id})
    except Exception:
        pass
    try:
        from backend.routes.chat_routes import save_message
        save_message("social_room", text, identity.get("display_name") or uid, is_ai=False)
    except Exception:
        pass
    reward = None
    return {"success": True, "message": row, "networks": targets, "fx": fx_id, "reward": reward}
