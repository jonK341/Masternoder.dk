"""Camgirls performer payout addresses."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PAYOUT_FILE = os.path.join(_ROOT, "data", "camgirls_payout_addresses.json")


def _read() -> dict:
    if not os.path.isfile(_PAYOUT_FILE):
        return {"performers": {}}
    try:
        with open(_PAYOUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"performers": {}}
    except Exception:
        return {"performers": {}}


def get_payout_address(performer_id: str) -> Dict[str, Any]:
    data = _read()
    row = (data.get("performers") or {}).get(performer_id) or {}
    return {"address": row.get("address"), "success": bool(row.get("address"))}
