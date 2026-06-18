"""Camgirls performer payout addresses — generated and owned by the MN2 daemon."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PAYOUT_FILE = os.path.join(_BASE, "data", "camgirls_payout_addresses.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_store() -> Dict[str, Any]:
    if not os.path.isfile(_PAYOUT_FILE):
        return {"performers": {}}
    try:
        with open(_PAYOUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"performers": {}}
        if not isinstance(data.get("performers"), dict):
            data["performers"] = {}
        return data
    except Exception:
        return {"performers": {}}


def _write_store(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PAYOUT_FILE), exist_ok=True)
    tmp = _PAYOUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _PAYOUT_FILE)


def _generate_daemon_address() -> Dict[str, Any]:
    """Fresh address from masternoder2d (same policy as user deposits)."""
    from backend.services.mn2_wallet_service import _generate_valid_address

    return _generate_valid_address()


def get_payout_address(performer_id: str) -> Optional[str]:
    pid = (performer_id or "").strip()
    if not pid:
        return None
    with _LOCK:
        store = _read_store()
        row = (store.get("performers") or {}).get(pid)
    if isinstance(row, dict):
        addr = (row.get("address") or "").strip()
        return addr or None
    return None


def get_or_create_payout_address(performer_id: str) -> Dict[str, Any]:
    """Return daemon payout address for performer; create via getnewaddress if missing."""
    pid = (performer_id or "").strip()
    if not pid:
        return {"success": False, "error": "performer_id_required"}

    existing = get_payout_address(pid)
    if existing:
        return {
            "success": True,
            "performer_id": pid,
            "payout_address": existing,
            "created": False,
        }

    gen = _generate_daemon_address()
    if not gen.get("success"):
        return {
            "success": False,
            "error": gen.get("error") or "daemon_getnewaddress_failed",
            "performer_id": pid,
        }

    addr = (gen.get("deposit_address") or "").strip()
    if not addr:
        return {"success": False, "error": "empty_address", "performer_id": pid}

    with _LOCK:
        store = _read_store()
        performers = store.setdefault("performers", {})
        if pid not in performers:
            performers[pid] = {
                "address": addr,
                "created_at": _iso(),
                "source": "daemon_getnewaddress",
            }
            store["updated_at"] = _iso()
            _write_store(store)
            created = True
        else:
            addr = (performers[pid].get("address") or addr).strip()
            created = False

    return {
        "success": True,
        "performer_id": pid,
        "payout_address": addr,
        "created": created,
    }


def list_payout_addresses() -> Dict[str, Any]:
    with _LOCK:
        store = _read_store()
    performers = store.get("performers") if isinstance(store.get("performers"), dict) else {}
    rows = []
    for pid, row in performers.items():
        if isinstance(row, dict):
            rows.append({
                "performer_id": pid,
                "payout_address": row.get("address"),
                "created_at": row.get("created_at"),
                "source": row.get("source"),
            })
    rows.sort(key=lambda r: r.get("performer_id") or "")
    return {"success": True, "addresses": rows, "count": len(rows)}


def provision_payout_addresses(*, performer_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Ensure every active performer has a daemon payout address."""
    from backend.services.camgirls_service import _load_performers_raw

    if performer_ids:
        targets = [(pid or "").strip() for pid in performer_ids if (pid or "").strip()]
    else:
        targets = [(row.get("id") or "").strip() for row in _load_performers_raw()]
        targets = [t for t in targets if t]

    results: List[Dict[str, Any]] = []
    ok = 0
    for pid in targets:
        r = get_or_create_payout_address(pid)
        results.append(r)
        if r.get("success"):
            ok += 1

    return {
        "success": ok == len(targets) if targets else True,
        "provisioned": ok,
        "total": len(targets),
        "results": results,
    }
