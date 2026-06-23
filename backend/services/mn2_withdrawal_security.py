"""
MN2 withdrawal security — address whitelist + TOTP 2FA (RFC 6238-style, no extra deps).

Storage: data/mn2_withdrawal_security.json
  {
    "<user_id>": {
      "whitelist": ["addr1", ...],
      "totp_secret": "BASE32...",
      "totp_enabled": true,
      "totp_verified_at": iso
    }
  }
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import threading
import time
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PATH = os.path.join(_BASE, "data", "mn2_withdrawal_security.json")


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_PATH):
        return {}
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _PATH)


def _user_row(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    row = data.setdefault(user_id, {})
    if not isinstance(row, dict):
        row = {}
        data[user_id] = row
    row.setdefault("whitelist", [])
    return row


def get_security_status(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    with _LOCK:
        row = _user_row(_load(), uid)
    wl = row.get("whitelist") or []
    if not isinstance(wl, list):
        wl = []
    return {
        "success": True,
        "user_id": uid,
        "whitelist": list(wl),
        "whitelist_count": len(wl),
        "totp_enabled": bool(row.get("totp_enabled")),
        "totp_configured": bool(row.get("totp_secret")),
    }


def add_whitelist_address(user_id: str, address: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    if not uid or not addr:
        return {"success": False, "error": "user_id and address required"}
    with _LOCK:
        data = _load()
        row = _user_row(data, uid)
        wl: List[str] = list(row.get("whitelist") or [])
        if addr not in wl:
            wl.append(addr)
        row["whitelist"] = wl
        _save(data)
    return {"success": True, "whitelist": wl}


def remove_whitelist_address(user_id: str, address: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    with _LOCK:
        data = _load()
        row = _user_row(data, uid)
        wl = [a for a in (row.get("whitelist") or []) if a != addr]
        row["whitelist"] = wl
        _save(data)
    return {"success": True, "whitelist": wl}


def is_address_whitelisted(user_id: str, address: str) -> bool:
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    with _LOCK:
        row = _user_row(_load(), uid)
        wl = row.get("whitelist") or []
    return addr in wl


def check_whitelist_gate(user_id: str, address: str, required: bool) -> Dict[str, Any]:
    if not required:
        return {"allowed": True}
    if is_address_whitelisted(user_id, address):
        return {"allowed": True}
    return {
        "allowed": False,
        "code": "whitelist_required",
        "error": "Withdrawals are restricted to whitelisted addresses. Add this address first.",
    }


def _b32_secret(length: int = 20) -> str:
    return base64.b32encode(secrets.token_bytes(length)).decode("ascii").strip("=")


def _totp_at(secret_b32: str, counter: int, digits: int = 6) -> str:
    pad = "=" * ((8 - len(secret_b32) % 8) % 8)
    key = base64.b32decode((secret_b32 + pad).upper())
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset: offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** digits)).zfill(digits)


def totp_code(secret_b32: str, period: int = 30, digits: int = 6, skew: int = 0) -> str:
    counter = int(time.time()) // period + skew
    return _totp_at(secret_b32, counter, digits)


def verify_totp(secret_b32: str, code: str, window: int = 1) -> bool:
    if not secret_b32 or not code:
        return False
    code = str(code).strip()
    if not code.isdigit() or len(code) != 6:
        return False
    period = 30
    base = int(time.time()) // period
    for skew in range(-window, window + 1):
        if _totp_at(secret_b32, base + skew) == code:
            return True
    return False


def setup_totp(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    secret = _b32_secret()
    with _LOCK:
        data = _load()
        row = _user_row(data, uid)
        row["totp_secret"] = secret
        row["totp_enabled"] = False
        row.pop("totp_verified_at", None)
        _save(data)
    issuer = "MasterNoder"
    label = uid
    uri = f"otpauth://totp/{issuer}:{label}?secret={secret}&issuer={issuer}&digits=6&period=30"
    return {"success": True, "secret": secret, "otpauth_uri": uri, "totp_enabled": False}


def enable_totp(user_id: str, code: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    with _LOCK:
        data = _load()
        row = _user_row(data, uid)
        secret = row.get("totp_secret")
        if not secret:
            return {"success": False, "error": "Call setup first"}
        if not verify_totp(secret, code):
            return {"success": False, "error": "Invalid verification code"}
        row["totp_enabled"] = True
        row["totp_verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _save(data)
    return {"success": True, "totp_enabled": True}


def disable_totp(user_id: str, code: Optional[str] = None) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    with _LOCK:
        data = _load()
        row = _user_row(data, uid)
        if row.get("totp_enabled") and row.get("totp_secret"):
            if not code or not verify_totp(row["totp_secret"], code):
                return {"success": False, "error": "Valid TOTP code required to disable"}
        row["totp_enabled"] = False
        row.pop("totp_secret", None)
        _save(data)
    return {"success": True, "totp_enabled": False}


def check_totp_gate(user_id: str, code: Optional[str]) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    with _LOCK:
        row = _user_row(_load(), uid)
        if not row.get("totp_enabled"):
            return {"allowed": True}
        secret = row.get("totp_secret")
    if not secret:
        return {"allowed": True}
    if verify_totp(secret, code or ""):
        return {"allowed": True}
    return {
        "allowed": False,
        "code": "totp_required",
        "error": "Two-factor authentication code required (6-digit TOTP).",
    }
