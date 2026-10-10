"""Discord server setup template + command registration helpers."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROFILE_PATH = os.path.join(_BASE, "data", "discord_app_profile.json")
_SERVER_PATH = os.path.join(_BASE, "data", "discord_server_setup.json")


def _load(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_app_profile() -> Dict[str, Any]:
    profile = _load(_PROFILE_PATH)
    return {"success": True, **profile}


def get_server_setup() -> Dict[str, Any]:
    setup = _load(_SERVER_PATH)
    guild = (os.environ.get("DISCORD_GUILD_ID") or "").strip()
    return {
        "success": True,
        "guild_id_configured": bool(guild),
        "guild_id": guild or None,
        **setup,
    }


_OPTION_TYPE_MAP = {
    "STRING": 3,
    "INTEGER": 4,
    "BOOLEAN": 5,
    "USER": 6,
    "CHANNEL": 7,
    "ROLE": 8,
    "MENTIONABLE": 9,
    "NUMBER": 10,
    "ATTACHMENT": 11,
}


def _normalize_option(opt: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(opt)
    raw = row.get("type")
    if isinstance(raw, str):
        row["type"] = _OPTION_TYPE_MAP.get(raw.upper(), 3)
    elif not isinstance(raw, int):
        row["type"] = 3
    if row.get("required") is not None:
        row["required"] = bool(row.get("required"))
    if not str(row.get("description") or "").strip():
        row["description"] = str(row.get("name") or "option").replace("_", " ")[:100]
    return row


def list_slash_command_payloads() -> List[Dict[str, Any]]:
    from backend.services.discord_controller_service import get_app_manifest

    manifest = get_app_manifest()
    rows: List[Dict[str, Any]] = []
    for cmd in manifest.get("commands") or []:
        if not isinstance(cmd, dict) or not cmd.get("name"):
            continue
        payload: Dict[str, Any] = {
            "name": str(cmd["name"])[:32],
            "description": str(cmd.get("description") or cmd["name"])[:100],
            "type": 1,
        }
        opts = cmd.get("options")
        if isinstance(opts, list) and opts:
            payload["options"] = [_normalize_option(o) for o in opts if isinstance(o, dict)]
        rows.append(payload)
    return rows


def register_global_commands(*, dry_run: bool = False) -> Dict[str, Any]:
    """PUT slash commands to Discord API (global registration)."""
    app_id = (os.environ.get("DISCORD_APPLICATION_ID") or os.environ.get("DISCORD_CLIENT_ID") or "").strip()
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    if not app_id or not token:
        return {
            "success": False,
            "error": "missing_credentials",
            "need": ["DISCORD_APPLICATION_ID or DISCORD_CLIENT_ID", "DISCORD_BOT_TOKEN"],
        }
    commands = list_slash_command_payloads()
    if dry_run:
        return {"success": True, "dry_run": True, "application_id": app_id, "commands": commands}
    url = f"https://discord.com/api/v10/applications/{app_id}/commands"
    body = json.dumps(commands).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "MasternoderBot/1.0 (+https://masternoder.dk)",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            registered = json.loads(raw) if raw else []
            return {
                "success": True,
                "application_id": app_id,
                "registered_count": len(registered) if isinstance(registered, list) else 0,
                "commands": registered,
            }
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:500]
        return {"success": False, "status": exc.code, "error": err or str(exc)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def validate_env_config() -> Dict[str, Any]:
    """Surface common misconfigurations (app id vs role id, missing bot token)."""
    app_id = (os.environ.get("DISCORD_APPLICATION_ID") or "").strip()
    client_id = (os.environ.get("DISCORD_CLIENT_ID") or "").strip()
    role_id = (os.environ.get("DISCORD_HOSTING_VIP_ROLE_ID") or "").strip()
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    pub = (os.environ.get("DISCORD_PUBLIC_KEY") or "").strip()
    issues: List[str] = []
    if not token:
        issues.append("DISCORD_BOT_TOKEN missing — reset token in Developer Portal → Bot")
    if not pub:
        issues.append("DISCORD_PUBLIC_KEY missing — copy from General Information")
    if app_id and role_id and app_id == role_id:
        issues.append("DISCORD_APPLICATION_ID must not equal DISCORD_HOSTING_VIP_ROLE_ID")
    if client_id and app_id and client_id != app_id:
        issues.append("DISCORD_APPLICATION_ID differs from DISCORD_CLIENT_ID — they should match")
    if not app_id and client_id:
        issues.append("Set DISCORD_APPLICATION_ID to match DISCORD_CLIENT_ID")
    return {
        "success": len(issues) == 0,
        "issues": issues,
        "configured": {
            "bot_token": bool(token),
            "public_key": bool(pub),
            "application_id": app_id or client_id or None,
            "guild_id": (os.environ.get("DISCORD_GUILD_ID") or "").strip() or None,
            "hosting_vip_role_id": role_id or None,
        },
        "interactions_url": "https://masternoder.dk/api/discord/interactions",
    }
