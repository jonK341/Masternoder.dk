"""Encrypted secrets vault + public wallet registry for exchange arbitrage.

One safe place for all sensitive credentials:
  - API keys / secrets / seeds  -> encrypted at rest (Fernet) in secrets_vault.enc
  - Public deposit addresses    -> plaintext registry (addresses are not secret)

The vault key comes from env ``EXCHANGE_VAULT_KEY``. If the value is a valid Fernet
key it is used directly; otherwise a Fernet key is derived from it via SHA-256 so any
passphrase works. If the ``cryptography`` package or the key is missing, writes of
secrets are refused (the system stays in paper mode) but the public registry still works.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_DATA_DIR = ex._DATA_DIR
_VAULT_PATH = os.path.join(_DATA_DIR, "secrets_vault.enc")
_REGISTRY_PATH = os.path.join(_DATA_DIR, "wallet_registry.json")
_LOCK = threading.RLock()


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fernet():
    """Return a Fernet instance, or None if unavailable."""
    raw = (os.environ.get("EXCHANGE_VAULT_KEY") or "").strip()
    if not raw:
        return None
    try:
        from cryptography.fernet import Fernet
    except Exception:
        return None
    try:
        key = raw.encode("utf-8")
        try:
            # Accept a ready-made Fernet key directly.
            return Fernet(key)
        except Exception:
            derived = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
            return Fernet(derived)
    except Exception:
        return None


def encryption_available() -> bool:
    return _fernet() is not None


def _load_vault() -> Dict[str, Any]:
    f = _fernet()
    if f is None or not os.path.isfile(_VAULT_PATH):
        return {}
    try:
        with open(_VAULT_PATH, "rb") as fh:
            blob = fh.read()
        if not blob:
            return {}
        data = json.loads(f.decrypt(blob).decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_vault(data: Dict[str, Any]) -> bool:
    f = _fernet()
    if f is None:
        return False
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        blob = f.encrypt(json.dumps(data, sort_keys=True).encode("utf-8"))
        tmp = _VAULT_PATH + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(blob)
        os.replace(tmp, _VAULT_PATH)
        return True
    except Exception:
        return False


def set_secret(name: str, value: str) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        return {"success": False, "error": "missing_name"}
    if not encryption_available():
        return {"success": False, "error": "encryption_unavailable",
                "hint": "Set EXCHANGE_VAULT_KEY and install 'cryptography' to store live secrets."}
    with _LOCK:
        vault = _load_vault()
        vault.setdefault("secrets", {})[name] = {"value": str(value), "updated_at": _iso()}
        if not _save_vault(vault):
            return {"success": False, "error": "save_failed"}
    ex._audit("vault_secret_set", user_id="admin", secret_name=name)
    return {"success": True, "name": name}


def get_secret(name: str) -> Optional[str]:
    name = (name or "").strip()
    if not name or not encryption_available():
        return None
    rec = (_load_vault().get("secrets") or {}).get(name)
    return rec.get("value") if isinstance(rec, dict) else None


def delete_secret(name: str) -> Dict[str, Any]:
    name = (name or "").strip()
    if not encryption_available():
        return {"success": False, "error": "encryption_unavailable"}
    with _LOCK:
        vault = _load_vault()
        if name in (vault.get("secrets") or {}):
            del vault["secrets"][name]
            _save_vault(vault)
    return {"success": True, "name": name}


def list_secret_names() -> List[str]:
    if not encryption_available():
        return []
    return sorted((_load_vault().get("secrets") or {}).keys())


def register_wallet(label: str, address: str, *, venue: str = "", asset: str = "", note: str = "") -> Dict[str, Any]:
    label = (label or "").strip()
    address = (address or "").strip()
    if not label or not address:
        return {"success": False, "error": "missing_label_or_address"}
    with _LOCK:
        reg = ex._read_json(_REGISTRY_PATH, {})
        if not isinstance(reg, dict):
            reg = {}
        reg.setdefault("wallets", {})[label] = {
            "address": address,
            "venue": venue,
            "asset": asset,
            "note": note,
            "updated_at": _iso(),
        }
        ex._write_json(_REGISTRY_PATH, reg)
    ex._audit("wallet_registered", user_id="admin", label=label, venue=venue, asset=asset)
    return {"success": True, "label": label}


def list_wallets() -> List[Dict[str, Any]]:
    reg = ex._read_json(_REGISTRY_PATH, {})
    wallets = (reg or {}).get("wallets") or {}
    out: List[Dict[str, Any]] = []
    for label, row in wallets.items():
        if isinstance(row, dict):
            out.append({"label": label, **row})
    return sorted(out, key=lambda r: r["label"])


def vault_status() -> Dict[str, Any]:
    return {
        "encryption_available": encryption_available(),
        "secret_count": len(list_secret_names()),
        "wallet_count": len(list_wallets()),
        "vault_file_exists": os.path.isfile(_VAULT_PATH),
    }
