"""Aggregate Discord channel members/messages into the customer directory."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_INDEX_FILE = os.path.join(_BASE, "data", "discord_customer_index.json")
_POINTS_DIR = os.path.join(_BASE, "logs", "unified_points")
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _config() -> Dict[str, Any]:
    try:
        with open(os.path.join(_BASE, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            root = json.load(f)
        block = root.get("discord_customers") if isinstance(root, dict) else {}
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def _bot_token() -> str:
    return (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()


def _guild_id() -> str:
    cfg = _config()
    return (os.environ.get("DISCORD_GUILD_ID") or cfg.get("guild_id") or "").strip()


def _customer_channel_id() -> str:
    cfg = _config()
    for key in ("DISCORD_CUSTOMER_CHANNEL_ID", "DISCORD_CHANNEL_CUSTOMERS_ID"):
        val = (os.environ.get(key) or cfg.get("channel_id") or "").strip()
        if val and not val.startswith("https://"):
            return val
    return ""


def _discord_api_get(path: str) -> Dict[str, Any]:
    token = _bot_token()
    if not token:
        return {"success": False, "error": "discord_bot_token_missing"}
    url = f"https://discord.com/api/v10{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "MasternoderBot/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
        data = json.loads(body) if body else []
        return {"success": True, "data": data}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:300]
        return {"success": False, "error": f"discord_http_{exc.code}", "detail": err_body}
    except Exception as exc:
        return {"success": False, "error": str(exc)[:200]}


def _load_index() -> Dict[str, Any]:
    if not os.path.isfile(_INDEX_FILE):
        return {"version": 1, "customers": {}, "last_sync_at": None, "channel_id": None}
    try:
        with open(_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("customers", {})
            return data
    except Exception:
        pass
    return {"version": 1, "customers": {}, "last_sync_at": None, "channel_id": None}


def _save_index(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_INDEX_FILE), exist_ok=True)
    tmp = _INDEX_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _INDEX_FILE)


def _prospect_user_id(discord_id: str) -> str:
    return f"discord_{discord_id}"


def _ensure_points_stub(user_id: str, discord_row: Dict[str, Any]) -> None:
    os.makedirs(_POINTS_DIR, exist_ok=True)
    path = os.path.join(_POINTS_DIR, f"{user_id}.json")
    if os.path.isfile(path):
        return
    stub = {
        "user_id": user_id,
        "level": 1,
        "xp_total": 0,
        "coins": 0,
        "mn2_balance": 0,
        "systems": {"mn2_balance": 0, "coins": 0},
        "source": "discord_channel",
        "discord": {
            "discord_id": discord_row.get("discord_id"),
            "username": discord_row.get("username"),
            "display_name": discord_row.get("display_name"),
            "channel_id": discord_row.get("channel_id"),
        },
        "updated_at": _iso(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stub, f, indent=2)


def _upsert_discord_customer(
    discord_id: str,
    *,
    username: str = "",
    display_name: str = "",
    channel_id: str = "",
    source: str = "channel_message",
    message_id: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services.discord_link_service import get_user_id_for_discord, link_user

    discord_id = str(discord_id or "").strip()
    if not discord_id:
        return {"success": False, "error": "discord_id_required"}

    linked_user = get_user_id_for_discord(discord_id)
    user_id = linked_user or _prospect_user_id(discord_id)

    row = {
        "discord_id": discord_id,
        "user_id": user_id,
        "username": username or discord_id,
        "display_name": display_name or username or discord_id,
        "channel_id": channel_id,
        "source": source,
        "linked": bool(linked_user),
        "last_seen_at": _iso(),
        "message_id": message_id,
    }

    index = _load_index()
    prev = index.get("customers", {}).get(discord_id) or {}
    if prev.get("first_seen_at"):
        row["first_seen_at"] = prev["first_seen_at"]
    else:
        row["first_seen_at"] = _iso()
    row["seen_count"] = int(prev.get("seen_count") or 0) + 1
    index.setdefault("customers", {})[discord_id] = row
    index["last_sync_at"] = _iso()
    index["channel_id"] = channel_id or index.get("channel_id")
    _save_index(index)

    if not linked_user:
        _ensure_points_stub(user_id, row)
    else:
        try:
            link_user(user_id, discord_id)
        except Exception:
            pass

    return {"success": True, "customer": row, "user_id": user_id}


def fetch_channel_messages(channel_id: str, *, limit: int = 100) -> Dict[str, Any]:
    cid = str(channel_id or "").strip()
    if not cid:
        return {"success": False, "error": "channel_id_required"}
    lim = max(1, min(100, int(limit)))
    res = _discord_api_get(f"/channels/{cid}/messages?limit={lim}")
    if not res.get("success"):
        return res
    messages = res.get("data") or []
    if not isinstance(messages, list):
        return {"success": False, "error": "invalid_messages_payload"}
    return {"success": True, "messages": messages, "count": len(messages)}


def fetch_guild_members(guild_id: str, *, limit: int = 1000) -> Dict[str, Any]:
    gid = str(guild_id or "").strip()
    if not gid:
        return {"success": False, "error": "guild_id_required"}
    lim = max(1, min(1000, int(limit)))
    res = _discord_api_get(f"/guilds/{gid}/members?limit={lim}")
    if not res.get("success"):
        return res
    members = res.get("data") or []
    if not isinstance(members, list):
        return {"success": False, "error": "invalid_members_payload"}
    return {"success": True, "members": members, "count": len(members)}


def sync_customers_from_channel(
    *,
    channel_id: Optional[str] = None,
    include_guild_members: bool = False,
    message_limit: int = 100,
) -> Dict[str, Any]:
    cfg = _config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "discord_customers_disabled"}

    cid = str(channel_id or _customer_channel_id() or "").strip()
    if not cid:
        return {"success": False, "error": "customer_channel_not_configured"}

    upserted: List[Dict[str, Any]] = []
    errors: List[str] = []

    msg_res = fetch_channel_messages(cid, limit=message_limit)
    if msg_res.get("success"):
        for msg in msg_res.get("messages") or []:
            author = (msg or {}).get("author") or {}
            if author.get("bot"):
                continue
            did = str(author.get("id") or "")
            if not did:
                continue
            row = _upsert_discord_customer(
                did,
                username=str(author.get("username") or ""),
                display_name=str(author.get("global_name") or author.get("username") or ""),
                channel_id=cid,
                source="channel_message",
                message_id=str(msg.get("id") or ""),
            )
            if row.get("success"):
                upserted.append(row["customer"])
    else:
        errors.append(msg_res.get("error") or "message_fetch_failed")

    if include_guild_members:
        gid = _guild_id()
        mem_res = fetch_guild_members(gid) if gid else {"success": False, "error": "guild_id_missing"}
        if mem_res.get("success"):
            for member in mem_res.get("members") or []:
                user = (member or {}).get("user") or {}
                if user.get("bot"):
                    continue
                did = str(user.get("id") or "")
                if not did:
                    continue
                row = _upsert_discord_customer(
                    did,
                    username=str(user.get("username") or ""),
                    display_name=str(member.get("nick") or user.get("global_name") or user.get("username") or ""),
                    channel_id=cid,
                    source="guild_member",
                )
                if row.get("success"):
                    upserted.append(row["customer"])
        else:
            errors.append(mem_res.get("error") or "member_fetch_failed")

    index = _load_index()
    return {
        "success": True,
        "channel_id": cid,
        "upserted_count": len(upserted),
        "total_indexed": len(index.get("customers") or {}),
        "last_sync_at": index.get("last_sync_at"),
        "errors": errors,
        "customers_preview": upserted[:20],
    }


def list_discord_customers(*, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    index = _load_index()
    rows = list((index.get("customers") or {}).values())
    rows.sort(key=lambda r: str(r.get("last_seen_at") or ""), reverse=True)
    total = len(rows)
    page = rows[offset: offset + limit]
    return {
        "success": True,
        "customers": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "last_sync_at": index.get("last_sync_at"),
        "channel_id": index.get("channel_id"),
    }


def discord_customer_stats() -> Dict[str, Any]:
    index = _load_index()
    customers = list((index.get("customers") or {}).values())
    linked = sum(1 for c in customers if c.get("linked"))
    return {
        "success": True,
        "total": len(customers),
        "linked": linked,
        "prospects": len(customers) - linked,
        "last_sync_at": index.get("last_sync_at"),
        "channel_id": index.get("channel_id"),
        "bot_configured": bool(_bot_token()),
        "guild_id": _guild_id() or None,
    }
