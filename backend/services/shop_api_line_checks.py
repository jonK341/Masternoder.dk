"""
Shop V.9 API line checks (historically “v4” in filenames) — shared by GET /api/shop/config and scripts/shop_v4_production_smoke.py.

Data file: data/shop_v4_api_line_checks.json
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_JSON = os.path.join(_PROJECT_ROOT, "data", "shop_v4_api_line_checks.json")
_DEFAULT_CHECKS = {
    "version": 1,
    "description": "Built-in fallback for Shop V.9 API line checks when data/shop_v4_api_line_checks.json is unavailable.",
    "checks": [
        {"label": "GET /api/shop/config", "path_template": "/api/shop/config", "kind": "success_not_false"},
        {"label": "GET /api/monetization/config", "path_template": "/api/monetization/config", "kind": "success_not_false"},
        {"label": "GET /api/game/shop/items", "path_template": "/api/game/shop/items", "kind": "shop_items_ok"},
        {"label": "GET /api/shop/coin-packs", "path_template": "/api/shop/coin-packs", "kind": "success_not_false"},
        {"label": "GET /api/shop/payment-health", "path_template": "/api/shop/payment-health", "kind": "payment_health_ok"},
        {"label": "GET /api/game/shop/currency", "path_template": "/api/game/shop/currency?user_id={{user_id}}", "kind": "success_not_false"},
        {"label": "GET /api/mn2/balance", "path_template": "/api/mn2/balance?user_id={{user_id}}", "kind": "success_true"},
        {"label": "GET /api/shop/inventory", "path_template": "/api/shop/inventory?user_id={{user_id}}", "kind": "success_not_false"},
        {"label": "GET /api/shop/purchases", "path_template": "/api/shop/purchases?user_id={{user_id}}&limit=5", "kind": "success_not_false"},
        {"label": "GET /api/points/comprehensive", "path_template": "/api/points/comprehensive?user_id={{user_id}}", "kind": "success_not_false"},
    ],
}


def load_shop_v4_api_line_checks(path: str | None = None) -> Dict[str, Any]:
    """Return parsed JSON or built-in checks on error."""
    p = path or _DEFAULT_JSON
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("checks"), list):
            return data
    except Exception:
        pass
    return {
        "version": _DEFAULT_CHECKS["version"],
        "description": _DEFAULT_CHECKS["description"],
        "checks": [dict(check) for check in _DEFAULT_CHECKS["checks"]],
        "source": "built_in_fallback",
    }


def expand_path_template(path_template: str, user_id: str) -> str:
    from urllib.parse import quote

    return path_template.replace("{{user_id}}", quote(user_id, safe=""))


def kind_ok(kind: str, body: Dict[str, Any]) -> bool:
    """Evaluate JSON response for a check kind (must match shop/index.html ShopV9)."""
    if not isinstance(body, dict):
        return False
    if kind == "success_not_false":
        return body.get("success") is not False
    if kind == "success_true":
        return body.get("success") is True
    if kind == "shop_items_ok":
        if body.get("success") is False:
            return False
        if "items" in body:
            return isinstance(body.get("items"), list)
        return body.get("success") is True
    if kind == "payment_health_ok":
        # Match JS !!(j.mn2_daemon || j.paypal): present keys count (empty {} is truthy in JS)
        return "mn2_daemon" in body or "paypal" in body
    return False
