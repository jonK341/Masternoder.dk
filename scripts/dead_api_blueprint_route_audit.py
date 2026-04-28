"""
Audit dead APIs/blueprints/routes from backend route files.

This script:
1) Statically extracts blueprints and route decorators from backend/routes/*.py
2) Probes production endpoints with safe methods (GET, POST)
3) Writes JSON + Markdown reports with counts and details
"""
from __future__ import annotations

import ast
import json
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROUTES_DIR = PROJECT_ROOT / "backend" / "routes"
REPORTS_DIR = PROJECT_ROOT / "reports"
BASE_URL = "https://masternoder.dk"
TIMEOUT_SECS = 6
MAX_WORKERS = 16


@dataclass
class RouteDef:
    file: str
    blueprint_var: str
    blueprint_name: str
    endpoint_func: str
    path: str
    methods: List[str]


def _sample_path(path: str) -> str:
    # Replace Flask converters with safe sample values.
    out = path
    while "<" in out and ">" in out:
        s = out.find("<")
        e = out.find(">", s)
        if e == -1:
            break
        token = out[s + 1 : e]
        if ":" in token:
            ctype, name = token.split(":", 1)
        else:
            ctype, name = "", token
        ctype = ctype.strip().lower()
        name = name.strip().lower()
        if ctype in {"int", "float"} or name.endswith("id") or name == "id":
            val = "1"
        elif ctype == "path":
            val = "sample/path"
        else:
            val = "sample"
        out = out[:s] + val + out[e + 1 :]
    return out


def _extract_routes_from_file(path: Path) -> Tuple[List[RouteDef], Optional[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [], f"SyntaxError line {exc.lineno}: {exc.msg}"

    blueprint_vars: Dict[str, str] = {}
    routes: List[RouteDef] = []

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        var = node.targets[0].id
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "Blueprint":
            bp_name = var
            if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                bp_name = call.args[0].value
            blueprint_vars[var] = bp_name

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            func = deco.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.attr == "route"
                and func.value.id in blueprint_vars
            ):
                continue

            route_path = None
            if deco.args and isinstance(deco.args[0], ast.Constant) and isinstance(deco.args[0].value, str):
                route_path = deco.args[0].value
            if not route_path:
                continue

            methods = ["GET"]
            for kw in deco.keywords:
                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    parsed = []
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            parsed.append(elt.value.upper())
                    if parsed:
                        methods = parsed
                    break

            routes.append(
                RouteDef(
                    file=str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    blueprint_var=func.value.id,
                    blueprint_name=blueprint_vars[func.value.id],
                    endpoint_func=node.name,
                    path=route_path,
                    methods=methods,
                )
            )

    return routes, None


def _extract_all_routes() -> Tuple[List[RouteDef], List[Dict[str, str]]]:
    all_routes: List[RouteDef] = []
    parse_errors: List[Dict[str, str]] = []
    for route_file in sorted(ROUTES_DIR.glob("*.py")):
        routes, err = _extract_routes_from_file(route_file)
        if err:
            parse_errors.append({"file": str(route_file.relative_to(PROJECT_ROOT)), "error": err})
        all_routes.extend(routes)
    return all_routes, parse_errors


def _is_api(path: str) -> bool:
    return path.startswith("/api/") or path.startswith("/vidgenerator/api/")


def _probe_one(path: str, methods: List[str]) -> Dict:
    method = None
    body = None

    allowed = {m.upper() for m in methods}
    if "GET" in allowed:
        method = "GET"
    elif "POST" in allowed:
        method = "POST"
        body = b"{}"
    else:
        return {"status": None, "class": "untested_unsafe_method", "method": None, "error": None}

    probe_path = _sample_path(path)
    url = BASE_URL.rstrip("/") + probe_path

    req = Request(url=url, method=method)
    req.add_header("User-Agent", "dead-route-audit/1.0")
    if method == "POST":
        req.add_header("Content-Type", "application/json")

    try:
        with urlopen(req, data=body, timeout=TIMEOUT_SECS, context=ssl.create_default_context()) as resp:
            code = int(resp.status)
    except HTTPError as e:
        code = int(e.code)
    except URLError as e:
        return {"status": None, "class": "dead_unreachable", "method": method, "error": str(e.reason)}
    except Exception as e:  # pragma: no cover - defensive
        return {"status": None, "class": "dead_unreachable", "method": method, "error": str(e)}

    if code in (500, 502, 503, 404):
        c = "dead"
    elif code in (400, 401, 403, 405):
        c = "alive_requires_input_or_auth"
    elif 200 <= code < 300:
        c = "healthy"
    else:
        c = "other"
    return {"status": code, "class": c, "method": method, "error": None}


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    routes, parse_errors = _extract_all_routes()
    api_routes = [r for r in routes if _is_api(r.path)]

    # De-duplicate identical route path+methods emitted by aliases/repeats.
    unique_map: Dict[Tuple[str, Tuple[str, ...]], RouteDef] = {}
    for r in api_routes:
        key = (r.path, tuple(sorted(set(m.upper() for m in r.methods))))
        unique_map.setdefault(key, r)
    unique_api_routes = list(unique_map.values())

    results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        future_to_route = {
            ex.submit(_probe_one, r.path, r.methods): r for r in unique_api_routes
        }
        for fut in as_completed(future_to_route):
            r = future_to_route[fut]
            probe = fut.result()
            results.append(
                {
                    "file": r.file,
                    "blueprint": r.blueprint_name,
                    "blueprint_var": r.blueprint_var,
                    "endpoint_func": r.endpoint_func,
                    "path": r.path,
                    "probe_path": _sample_path(r.path),
                    "declared_methods": r.methods,
                    "probe_method": probe["method"],
                    "status": probe["status"],
                    "classification": probe["class"],
                    "error": probe["error"],
                }
            )

    by_blueprint: Dict[str, Dict[str, int]] = {}
    by_file: Dict[str, Dict[str, int]] = {}
    for row in results:
        bp = row["blueprint"]
        f = row["file"]
        for bucket, key in ((by_blueprint, bp), (by_file, f)):
            if key not in bucket:
                bucket[key] = {"total": 0, "tested": 0, "dead": 0, "healthy": 0, "alive_requires_input_or_auth": 0, "other": 0, "untested_unsafe_method": 0, "dead_unreachable": 0}
            bucket[key]["total"] += 1
            bucket[key][row["classification"]] += 1
            if row["classification"] != "untested_unsafe_method":
                bucket[key]["tested"] += 1

    dead_routes = [r for r in results if r["classification"] in {"dead", "dead_unreachable"}]
    dead_blueprints = [
        k for k, s in by_blueprint.items()
        if s["tested"] > 0 and (s["dead"] + s["dead_unreachable"]) == s["tested"]
    ]
    dead_route_files = [
        k for k, s in by_file.items()
        if s["tested"] > 0 and (s["dead"] + s["dead_unreachable"]) == s["tested"]
    ]

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "parse_errors": parse_errors,
        "summary": {
            "route_files_scanned": len(list(ROUTES_DIR.glob("*.py"))),
            "route_files_with_parse_errors": len(parse_errors),
            "api_routes_extracted_total": len(api_routes),
            "api_routes_unique_path_method": len(unique_api_routes),
            "api_routes_dead_count": len(dead_routes),
            "dead_blueprints_count": len(dead_blueprints),
            "dead_route_files_count": len(dead_route_files),
        },
        "dead_blueprints": dead_blueprints,
        "dead_route_files": dead_route_files,
        "blueprint_stats": by_blueprint,
        "route_file_stats": by_file,
        "dead_routes": dead_routes,
        "all_results": results,
    }

    json_path = REPORTS_DIR / "dead_api_blueprint_route_audit.json"
    md_path = REPORTS_DIR / "dead_api_blueprint_route_audit.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Dead API / Blueprint / Route Audit",
        "",
        f"- Generated: {report['generated_at_utc']}",
        f"- Base URL: `{BASE_URL}`",
        "",
        "## Summary",
        "",
        f"- Route files scanned: **{report['summary']['route_files_scanned']}**",
        f"- Route files with parse errors: **{report['summary']['route_files_with_parse_errors']}**",
        f"- API routes extracted (all): **{report['summary']['api_routes_extracted_total']}**",
        f"- API routes unique (path+methods): **{report['summary']['api_routes_unique_path_method']}**",
        f"- Dead API routes: **{report['summary']['api_routes_dead_count']}**",
        f"- Dead blueprints: **{report['summary']['dead_blueprints_count']}**",
        f"- Dead route files: **{report['summary']['dead_route_files_count']}**",
        "",
        "## Dead Blueprints",
        "",
    ]
    if dead_blueprints:
        lines.extend([f"- `{b}`" for b in dead_blueprints[:100]])
    else:
        lines.append("- None")

    lines.extend(["", "## Dead Route Files", ""])
    if dead_route_files:
        lines.extend([f"- `{f}`" for f in dead_route_files[:100]])
    else:
        lines.append("- None")

    lines.extend(["", "## Dead Routes (first 200)", ""])
    if dead_routes:
        for r in dead_routes[:200]:
            lines.append(
                f"- `{r['path']}` [{r['probe_method']}] -> {r['status']} ({r['classification']}) in `{r['file']}`"
            )
    else:
        lines.append("- None")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("Audit complete")
    print(f"Dead API routes: {report['summary']['api_routes_dead_count']}")
    print(f"Dead blueprints: {report['summary']['dead_blueprints_count']}")
    print(f"Dead route files: {report['summary']['dead_route_files_count']}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

