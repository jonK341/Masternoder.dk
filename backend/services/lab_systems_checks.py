"""
Lab hub API line checks — shared by GET /api/lab/systems-check and lab UI systems tab.

Data file: data/lab_systems_checks.json
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from backend.services.shop_api_line_checks import expand_path_template, kind_ok

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_JSON = os.path.join(_PROJECT_ROOT, "data", "lab_systems_checks.json")

_DEFAULT_CHECKS = {
    "version": 1,
    "description": "Built-in fallback lab systems checks.",
    "checks": [
        {"label": "GET /api/lab/v2/status", "path_template": "/api/lab/v2/status?user_id={{user_id}}", "kind": "success_true"},
        {"label": "GET /api/lab/progression", "path_template": "/api/lab/progression?user_id={{user_id}}", "kind": "success_true"},
        {"label": "GET /api/lab/overview", "path_template": "/api/lab/overview?user_id={{user_id}}", "kind": "success_true"},
    ],
}


def load_lab_systems_checks(path: str | None = None) -> Dict[str, Any]:
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
        "checks": [dict(c) for c in _DEFAULT_CHECKS["checks"]],
        "source": "built_in_fallback",
    }


def lab_kind_ok(kind: str, body: Dict[str, Any]) -> bool:
    if kind == "trophy_defs_ok":
        if not isinstance(body, dict):
            return False
        return isinstance(body.get("trophies"), list) or body.get("success") is not False
    return kind_ok(kind, body)


def run_lab_systems_checks(app, user_id: str) -> Dict[str, Any]:
    """Run all lab checks via Flask test client (in-process, no network)."""
    spec = load_lab_systems_checks()
    checks = spec.get("checks") or []
    results: List[Dict[str, Any]] = []
    passed = 0
    with app.test_client() as client:
        for row in checks:
            if not isinstance(row, dict):
                continue
            label = row.get("label") or row.get("path_template") or "check"
            path = expand_path_template(str(row.get("path_template") or "/"), user_id)
            kind = str(row.get("kind") or "success_not_false")
            ok = False
            status = 0
            err = None
            try:
                resp = client.get(path)
                status = resp.status_code
                body = resp.get_json(silent=True) or {}
                ok = status < 500 and lab_kind_ok(kind, body if isinstance(body, dict) else {})
            except Exception as exc:
                err = str(exc)
            if ok:
                passed += 1
            entry = {"label": label, "path": path, "kind": kind, "ok": ok, "status": status}
            if err:
                entry["error"] = err
            results.append(entry)
    total = len(results)
    return {
        "version": spec.get("version", 1),
        "description": spec.get("description", ""),
        "passed": passed,
        "total": total,
        "all_ok": passed == total and total > 0,
        "checks": results,
    }
