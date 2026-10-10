"""Camgirls performer payout addresses."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PAYOUT_FILE = os.path.join(_ROOT, "data", "camgirls_payout_addresses.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read() -> dict:
    if not os.path.isfile(_PAYOUT_FILE):
        return {"performers": {}}
    try:
        with open(_PAYOUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"performers": {}}
    except Exception:
        return {"performers": {}}


def _write(data: dict) -> None:
    os.makedirs(os.path.dirname(_PAYOUT_FILE), exist_ok=True)
    with open(_PAYOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_payout_address(performer_id: str) -> Dict[str, Any]:
    data = _read()
    row = (data.get("performers") or {}).get(performer_id) or {}
    return {"address": row.get("address"), "success": bool(row.get("address"))}


def list_payout_addresses() -> Dict[str, Any]:
    data = _read()
    performers = data.get("performers") or {}
    rows = [
        {"performer_id": pid, "payout_address": (row or {}).get("address"), "created_at": (row or {}).get("created_at")}
        for pid, row in performers.items()
        if isinstance(row, dict)
    ]
    return {"success": True, "count": len(rows), "performers": rows}


def provision_payout_addresses(performer_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    from backend.services.camgirls_service import _load_performers_raw
    from backend.services.mn2_wallet_service import generate_daemon_address

    targets = performer_ids or [str(p.get("id")) for p in _load_performers_raw() if p.get("id")]
    targets = [t for t in targets if t]
    data = _read()
    bucket = data.setdefault("performers", {})
    results: List[Dict[str, Any]] = []
    ok_count = 0
    for pid in targets:
        existing = bucket.get(pid) if isinstance(bucket.get(pid), dict) else None
        if existing and existing.get("address"):
            results.append({
                "success": True,
                "performer_id": pid,
                "payout_address": existing.get("address"),
                "created": False,
            })
            ok_count += 1
            continue
        gen = generate_daemon_address()
        if not gen.get("success"):
            results.append({
                "success": False,
                "performer_id": pid,
                "error": gen.get("error") or "address_failed",
            })
            continue
        addr = gen.get("address") or gen.get("deposit_address")
        bucket[pid] = {"address": addr, "created_at": _iso(), "source": "mn2_daemon"}
        results.append({
            "success": True,
            "performer_id": pid,
            "payout_address": addr,
            "created": True,
        })
        ok_count += 1
    _write(data)
    return {
        "success": ok_count == len(targets) if targets else True,
        "provisioned": ok_count,
        "total": len(targets),
        "results": results,
    }
