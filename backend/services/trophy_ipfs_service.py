"""Content-addressed permanent metadata storage (IPFS-compatible URIs)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MANIFEST_PATH = os.path.join(_BASE, "data", "trophy_ipfs_manifest.json")
_CONFIG_PATH = os.path.join(_BASE, "data", "trophy_ipfs_config.json")


def _storage_dir() -> str:
    return os.path.join(_BASE, "static", "trophy-ipfs", "cid")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with _LOCK:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        return True
    except Exception:
        return False


def get_config() -> Dict[str, Any]:
    return _read_json(
        _CONFIG_PATH,
        {
            "enabled": True,
            "auto_pin_on_grant": True,
            "auto_pin_on_proof_view": True,
            "gateway_base": "/static/trophy-ipfs/cid",
            "pin_api_url": "",
        },
    )


def content_digest(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ipfs_uri_for_digest(digest: str) -> str:
    return f"ipfs://{digest}"


def gateway_url_for_digest(digest: str) -> str:
    cfg = get_config()
    base = (cfg.get("gateway_base") or "/static/trophy-ipfs/cid").rstrip("/")
    return f"{base}/{digest}.json"


def _maybe_remote_pin(digest: str, file_path: str) -> Dict[str, Any]:
    cfg = get_config()
    api_url = (cfg.get("pin_api_url") or os.environ.get("IPFS_PIN_API_URL") or "").strip()
    if not api_url:
        return {"skipped": True, "reason": "no_pin_api"}

    try:
        with open(file_path, "rb") as f:
            body = f.read()
        req = urlrequest.Request(
            api_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return {"success": True, "remote_pin": True, "response": raw[:500]}
    except urlerror.URLError as exc:
        return {"success": False, "error": str(exc), "remote_pin": False}
    except Exception as exc:
        return {"success": False, "error": str(exc), "remote_pin": False}


def pin_edition_metadata(edition_key: str, *, force: bool = False) -> Dict[str, Any]:
    """Write canonical metadata JSON to content-addressed storage."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "ipfs_disabled"}

    ekey = (edition_key or "").strip()
    if not ekey:
        return {"success": False, "error": "missing_edition_key"}

    manifest = _read_json(_MANIFEST_PATH, {"pins": {}})
    pins = manifest.setdefault("pins", {})
    if not force and isinstance(pins.get(ekey), dict) and pins[ekey].get("digest"):
        row = pins[ekey]
        return {
            "success": True,
            "edition_key": ekey,
            "digest": row.get("digest"),
            "ipfs_uri": row.get("ipfs_uri"),
            "gateway_url": row.get("gateway_url"),
            "skipped": True,
        }

    from backend.services.trophy_metadata_service import build_metadata

    meta = build_metadata(ekey)
    if not meta.get("success"):
        return meta

    payload = meta.get("metadata") or {}
    digest = content_digest(payload)
    storage_dir = _storage_dir()
    os.makedirs(storage_dir, exist_ok=True)
    out_path = os.path.join(storage_dir, f"{digest}.json")
    if force or not os.path.isfile(out_path):
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    ipfs_uri = ipfs_uri_for_digest(digest)
    gateway_url = gateway_url_for_digest(digest)
    remote = _maybe_remote_pin(digest, out_path)

    pins[ekey] = {
        "edition_key": ekey,
        "digest": digest,
        "ipfs_uri": ipfs_uri,
        "gateway_url": gateway_url,
        "pinned_at": _iso(),
        "remote_pin": remote,
    }
    manifest["updated_at"] = _iso()
    _write_json(_MANIFEST_PATH, manifest)

    try:
        from backend.services.trophy_fulfillment_service import patch_edition_fields

        edition = meta.get("edition") or {}
        owner = meta.get("owner_id") or ""
        iid = edition.get("item_id") or ""
        eno = int(edition.get("edition_no") or 0)
        if owner and iid and eno:
            patch_edition_fields(
                str(owner),
                str(iid),
                eno,
                {"ipfs_uri": ipfs_uri, "ipfs_gateway_url": gateway_url, "ipfs_digest": digest},
            )
    except Exception:
        pass

    return {
        "success": True,
        "edition_key": ekey,
        "digest": digest,
        "ipfs_uri": ipfs_uri,
        "gateway_url": gateway_url,
        "skipped": False,
        "remote_pin": remote,
    }


def get_pin_status(edition_key: str) -> Dict[str, Any]:
    ekey = (edition_key or "").strip()
    pins = (_read_json(_MANIFEST_PATH, {"pins": {}}).get("pins") or {})
    row = pins.get(ekey)
    if not row:
        return {"success": True, "edition_key": ekey, "pinned": False}
    return {"success": True, "edition_key": ekey, "pinned": True, **row}
