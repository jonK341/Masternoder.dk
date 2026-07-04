"""Camgirls studio catalog — gifts, dances, tip menu."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CATALOG_FILE = os.path.join(_ROOT, "data", "camgirls_studio_catalog.json")


def studio_catalog() -> Dict[str, Any]:
    if not os.path.isfile(_CATALOG_FILE):
        return {"success": False, "error": "catalog_missing"}
    try:
        with open(_CATALOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"success": False, "error": "invalid_catalog"}
        return {"success": True, **data}
    except Exception as e:
        return {"success": False, "error": str(e)}
