"""
Provably-fair RNG for the casino.

Each outcome is derived from HMAC_SHA256(server_seed, "{client_seed}:{nonce}").
The server seed is committed as a SHA-256 hash *before* play and only revealed
after the player rotates their seed, so any past round can be independently
recomputed with verify().

State per user lives in logs/casino_fairness.json (consistent with the rest of
the casino's flat-file storage). All money still flows through casino_service;
this module only produces deterministic, auditable random floats in [0, 1).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
from typing import Any, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOCK = threading.Lock()

# 52 bits of entropy per draw (13 hex chars), the bitcoin provably-fair standard.
_HEX_DIGITS = 13
_DENOM = float(1 << 52)


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _state_path() -> str:
    log_dir = _log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_fairness.json")


def _load_all() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_all(data: Dict[str, Any]) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        # Never fail a bet because the fairness log is not writable.
        pass


def _hash_seed(server_seed: str) -> str:
    return hashlib.sha256(server_seed.encode("utf-8")).hexdigest()


def hmac_float(server_seed: str, client_seed: str, nonce: int) -> float:
    """Pure: deterministic float in [0, 1) for a (server, client, nonce) triple."""
    message = f"{client_seed}:{int(nonce)}".encode("utf-8")
    digest = hmac.new(server_seed.encode("utf-8"), message, hashlib.sha256).hexdigest()
    value = int(digest[:_HEX_DIGITS], 16)
    return value / _DENOM


def verify(server_seed: str, client_seed: str, nonce: int) -> Dict[str, Any]:
    """Pure: recompute a past outcome and confirm the revealed seed's hash."""
    return {
        "server_seed": server_seed,
        "server_seed_hash": _hash_seed(server_seed),
        "client_seed": client_seed,
        "nonce": int(nonce),
        "float": hmac_float(server_seed, client_seed, nonce),
    }


def _new_state() -> Dict[str, Any]:
    server_seed = secrets.token_hex(32)
    return {
        "server_seed": server_seed,
        "server_seed_hash": _hash_seed(server_seed),
        "client_seed": secrets.token_hex(8),
        "nonce": 0,
        "previous": None,
    }


def _ensure(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    state = data.get(user_id)
    if not isinstance(state, dict) or not state.get("server_seed"):
        state = _new_state()
        data[user_id] = state
    return state


def public_state(user_id: str) -> Dict[str, Any]:
    """Public commitment for a user: the server seed *hash*, client seed, nonce."""
    with _LOCK:
        data = _load_all()
        state = _ensure(data, user_id)
        _save_all(data)
        prev = state.get("previous") if isinstance(state.get("previous"), dict) else None
        return {
            "success": True,
            "server_seed_hash": state["server_seed_hash"],
            "client_seed": state["client_seed"],
            "nonce": int(state.get("nonce") or 0),
            "previous": {
                "server_seed": prev.get("server_seed"),
                "server_seed_hash": prev.get("server_seed_hash"),
                "client_seed": prev.get("client_seed"),
                "nonce_count": prev.get("nonce_count"),
            } if prev else None,
        }


def draw(user_id: str) -> Dict[str, Any]:
    """Consume one outcome: bump the nonce and return the float plus its proof."""
    with _LOCK:
        data = _load_all()
        state = _ensure(data, user_id)
        nonce = int(state.get("nonce") or 0) + 1
        state["nonce"] = nonce
        server_seed = state["server_seed"]
        client_seed = state["client_seed"]
        _save_all(data)
    return {
        "float": hmac_float(server_seed, client_seed, nonce),
        "server_seed_hash": _hash_seed(server_seed),
        "client_seed": client_seed,
        "nonce": nonce,
    }


def set_client_seed(user_id: str, client_seed: str) -> Dict[str, Any]:
    seed = (client_seed or "").strip()[:128]
    if not seed:
        return {"success": False, "error": "client_seed required"}
    with _LOCK:
        data = _load_all()
        state = _ensure(data, user_id)
        state["client_seed"] = seed
        _save_all(data)
    return public_state(user_id)


def rotate(user_id: str, new_client_seed: Optional[str] = None) -> Dict[str, Any]:
    """Reveal the current server seed (so prior rounds verify) and commit a new one."""
    with _LOCK:
        data = _load_all()
        state = _ensure(data, user_id)
        revealed = {
            "server_seed": state["server_seed"],
            "server_seed_hash": state["server_seed_hash"],
            "client_seed": state["client_seed"],
            "nonce_count": int(state.get("nonce") or 0),
        }
        fresh = _new_state()
        if new_client_seed and str(new_client_seed).strip():
            fresh["client_seed"] = str(new_client_seed).strip()[:128]
        fresh["previous"] = revealed
        data[user_id] = fresh
        _save_all(data)
    return {
        "success": True,
        "revealed": revealed,
        "server_seed_hash": fresh["server_seed_hash"],
        "client_seed": fresh["client_seed"],
        "nonce": 0,
    }
