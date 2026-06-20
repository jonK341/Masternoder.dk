"""C6 — Discord hosting VIP role (M8 #51 extension for paid hosting customers)."""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_GRANTS_LOG = os.path.join(_BASE, "logs", "discord_role_grants.jsonl")
_PENDING_LOG = os.path.join(_BASE, "logs", "discord_pending_hosting_vip.jsonl")


def _iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _append_log(path: str, row: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with _LOCK:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def user_has_paid_hosting(user_id: str) -> bool:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return False
    try:
        from backend.services.mn2_masternode_hosting_service import list_user_orders

        return any(o.get("status") == "paid" for o in list_user_orders(uid, limit=50))
    except Exception:
        return False


def _bot_config() -> Dict[str, Optional[str]]:
    return {
        "token": (os.environ.get("DISCORD_BOT_TOKEN") or "").strip(),
        "guild_id": (os.environ.get("DISCORD_GUILD_ID") or "").strip(),
        "role_id": (os.environ.get("DISCORD_HOSTING_VIP_ROLE_ID") or "").strip(),
    }


def _discord_put_member_role(guild_id: str, discord_user_id: str, role_id: str, token: str) -> Dict[str, Any]:
    url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{discord_user_id}/roles/{role_id}"
    req = urllib.request.Request(
        url,
        data=b"",
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "MasternoderBot/1.0 (+https://masternoder.dk)",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            return {"success": ok, "status": resp.status}
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return {"success": False, "status": exc.code, "error": body or f"HTTP {exc.code}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def queue_pending_hosting_vip(user_id: str, *, reason: str = "hosting_paid") -> None:
    _append_log(_PENDING_LOG, {"ts": _iso(), "user_id": user_id, "reason": reason, "status": "pending"})


def grant_hosting_vip_role(user_id: str, *, reason: str = "hosting_paid") -> Dict[str, Any]:
    """Assign Discord hosting VIP role when user is linked and bot is configured."""
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "missing_user"}

    if not user_has_paid_hosting(uid):
        return {"success": False, "error": "no_paid_hosting", "eligible": False}

    from backend.services.discord_link_service import get_discord_id_for_user

    discord_id = get_discord_id_for_user(uid)
    cfg = _bot_config()
    if not cfg["token"] or not cfg["guild_id"] or not cfg["role_id"]:
        if discord_id:
            queue_pending_hosting_vip(uid, reason=reason)
        return {
            "success": True,
            "pending": True,
            "reason": "bot_not_configured",
            "eligible": True,
            "discord_linked": bool(discord_id),
        }

    if not discord_id:
        queue_pending_hosting_vip(uid, reason=reason)
        return {
            "success": True,
            "pending": True,
            "reason": "discord_not_linked",
            "eligible": True,
        }

    api = _discord_put_member_role(cfg["guild_id"], discord_id, cfg["role_id"], cfg["token"])
    row = {
        "ts": _iso(),
        "user_id": uid,
        "discord_id": discord_id,
        "role_id": cfg["role_id"],
        "reason": reason,
        "success": api.get("success"),
        "error": api.get("error"),
    }
    _append_log(_GRANTS_LOG, row)

    if api.get("success"):
        return {
            "success": True,
            "granted": True,
            "user_id": uid,
            "discord_id": discord_id,
            "role": "hosting_vip",
        }

    err = str(api.get("error") or "")
    if api.get("status") in (403, 404):
        queue_pending_hosting_vip(uid, reason=reason)
    return {
        "success": False,
        "granted": False,
        "error": err or "role_grant_failed",
        "discord_id": discord_id,
    }


def sync_pending_for_user(user_id: str) -> Dict[str, Any]:
    """Retry role grant after Discord link (M8 #51 flow)."""
    return grant_hosting_vip_role(user_id, reason="discord_linked_sync")


def check_hosting_vip_eligibility(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    from backend.services.discord_link_service import get_discord_id_for_user

    discord_id = get_discord_id_for_user(uid)
    paid = user_has_paid_hosting(uid)
    cfg = _bot_config()
    bot_ready = bool(cfg["token"] and cfg["guild_id"] and cfg["role_id"])
    eligible = paid and bool(discord_id) and bot_ready
    return {
        "success": True,
        "user_id": uid,
        "hosting_customer": paid,
        "discord_linked": bool(discord_id),
        "discord_id": discord_id,
        "bot_configured": bot_ready,
        "eligible": eligible,
        "role": "hosting_vip" if eligible else None,
        "link_href": "/profile#discord-link",
        "message": (
            "Hosting VIP Discord role ready."
            if eligible
            else (
                "Link Discord on Profile after your hosting payment to receive the VIP role."
                if paid and not discord_id
                else "Pay for a masternode hosting slot to unlock the Discord VIP role."
            )
        ),
    }


def list_pending_grants(limit: int = 50) -> List[Dict[str, Any]]:
    if not os.path.isfile(_PENDING_LOG):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(_PENDING_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return rows[-limit:]
