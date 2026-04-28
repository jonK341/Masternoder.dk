"""
Scan registered Flask API endpoints and report dead routes.

Dead route definition in this scanner:
- HTTP 500/502/503
- HTTP 404 for a registered route probe

Not counted as dead:
- 400/401/403 (likely missing auth or required input)
- 405 (method mismatch)
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run import app


PARAM_RE = re.compile(r"<(?:(\w+):)?(\w+)>")


def _sample_value(type_name: str | None, var_name: str) -> str:
    if type_name in {"int", "float"}:
        return "1"
    if type_name == "path":
        return "sample/path"
    if "id" in var_name.lower():
        return "1"
    if "slug" in var_name.lower():
        return "sample-slug"
    return "sample"


def _materialize_rule(rule: str) -> str:
    def repl(match: re.Match) -> str:
        type_name = match.group(1)
        var_name = match.group(2)
        return _sample_value(type_name, var_name)

    return PARAM_RE.sub(repl, rule)


def _is_api_path(path: str) -> bool:
    return path.startswith("/api/") or path.startswith("/vidgenerator/api/")


def _scan_routes() -> Dict:
    client = app.test_client()

    route_results: List[Dict] = []
    blueprint_stats: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {
            "routes_total": 0,
            "routes_tested": 0,
            "healthy": 0,
            "dead": 0,
            "requires_input_or_auth": 0,
            "other": 0,
        }
    )

    api_rules = sorted(
        [r for r in app.url_map.iter_rules() if _is_api_path(r.rule)],
        key=lambda r: r.rule,
    )

    for rule in api_rules:
        methods = set(rule.methods or set())
        bp_name = rule.endpoint.split(".")[0] if "." in rule.endpoint else "root"
        blueprint_stats[bp_name]["routes_total"] += 1

        # Probe GET only to avoid side effects.
        if "GET" not in methods:
            route_results.append(
                {
                    "rule": rule.rule,
                    "probe_path": None,
                    "endpoint": rule.endpoint,
                    "blueprint": bp_name,
                    "methods": sorted(methods),
                    "status": None,
                    "classification": "skipped_non_get",
                }
            )
            continue

        probe_path = _materialize_rule(rule.rule)
        status_code = None
        classification = "unknown"
        error_text = None

        try:
            response = client.get(probe_path)
            status_code = int(response.status_code)

            if status_code in (500, 502, 503, 404):
                classification = "dead"
                blueprint_stats[bp_name]["dead"] += 1
            elif status_code in (400, 401, 403):
                classification = "requires_input_or_auth"
                blueprint_stats[bp_name]["requires_input_or_auth"] += 1
            elif 200 <= status_code < 300:
                classification = "healthy"
                blueprint_stats[bp_name]["healthy"] += 1
            else:
                classification = "other"
                blueprint_stats[bp_name]["other"] += 1

        except Exception as exc:  # Defensive: request handler crash
            classification = "dead"
            blueprint_stats[bp_name]["dead"] += 1
            error_text = f"{type(exc).__name__}: {exc}"

        blueprint_stats[bp_name]["routes_tested"] += 1
        route_results.append(
            {
                "rule": rule.rule,
                "probe_path": probe_path,
                "endpoint": rule.endpoint,
                "blueprint": bp_name,
                "methods": sorted(methods),
                "status": status_code,
                "classification": classification,
                "error": error_text,
            }
        )

    dead_routes = [r for r in route_results if r["classification"] == "dead"]
    dead_blueprints = [
        name
        for name, stats in blueprint_stats.items()
        if stats["routes_tested"] > 0 and stats["dead"] == stats["routes_tested"]
    ]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "api_routes_total": len(api_rules),
            "api_routes_tested_get": sum(1 for r in route_results if r["probe_path"]),
            "api_routes_dead": len(dead_routes),
            "blueprints_total": len(blueprint_stats),
            "blueprints_with_all_routes_dead": len(dead_blueprints),
        },
        "dead_blueprints": dead_blueprints,
        "blueprint_stats": dict(blueprint_stats),
        "dead_routes": dead_routes,
        "all_route_results": route_results,
    }


def main() -> int:
    report = _scan_routes()
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dead_endpoint_scan.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary = report["summary"]
    print("Dead endpoint scan complete")
    print(f"API routes total: {summary['api_routes_total']}")
    print(f"API routes tested (GET): {summary['api_routes_tested_get']}")
    print(f"Dead API routes: {summary['api_routes_dead']}")
    print(f"Blueprints total: {summary['blueprints_total']}")
    print(
        f"Blueprints with all routes dead: {summary['blueprints_with_all_routes_dead']}"
    )
    print(f"Report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

