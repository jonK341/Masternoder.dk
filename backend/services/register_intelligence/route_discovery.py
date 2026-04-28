"""Route Discovery - Scans backend for blueprints and route definitions."""
import os
import re
from typing import List, Dict, Tuple, Optional

BLUEPRINT_PATTERN = re.compile(r"^(\w+_bp)\s*=\s*Blueprint\s*\(\s*['\"](\w+)['\"]")
ROUTE_DECORATOR_PATTERN = re.compile(r"@\w+\.route\s*\(\s*['\"]([^'\"]+)['\"]")
ROUTE_SIMPLE_PATTERN = re.compile(r"@(\w+_bp)\.route\s*\(\s*['\"]([^'\"]+)['\"]")


def discover_blueprints(project_root: str) -> List[Dict]:
    """Discover blueprint definitions in backend/routes and vidgenerator/src/routes."""
    results = []
    for search_dir in [
        os.path.join(project_root, "backend", "routes"),
        os.path.join(project_root, "vidgenerator", "src", "routes"),
    ]:
        if not os.path.isdir(search_dir):
            continue
        for fname in sorted(os.listdir(search_dir)):
            if not fname.endswith(".py") or fname.startswith("_") or ".backup" in fname:
                continue
            path = os.path.join(search_dir, fname)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                for m in BLUEPRINT_PATTERN.finditer(content):
                    bp_var, bp_name = m.group(1), m.group(2)
                    rel = os.path.relpath(path, project_root)
                    module = rel.replace(os.sep, ".").replace(".py", "")
                    results.append({
                        "module_path": module, "bp_var": bp_var, "bp_name": bp_name,
                        "file_path": path, "import_path": "from %s import %s" % (module, bp_var),
                    })
            except Exception:
                pass
    return results


def discover_routes_from_blueprints(project_root: str, blueprint_files: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """Discover route paths from blueprint route decorators."""
    if blueprint_files is None:
        bps = discover_blueprints(project_root)
        blueprint_files = list({b["file_path"] for b in bps})
    routes_by_bp = {}
    for path in blueprint_files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            bp_match = BLUEPRINT_PATTERN.search(content)
            bp_var = bp_match.group(1) if bp_match else None
            if not bp_var:
                continue
            routes = [m.group(1) for m in ROUTE_DECORATOR_PATTERN.finditer(content) if m.group(1) and not m.group(1).startswith("/static")]
            if routes:
                routes_by_bp[bp_var] = list(dict.fromkeys(routes))
        except Exception:
            pass
    return routes_by_bp


def discover_routes_simple(project_root: str) -> List[Tuple[str, str]]:
    """Return (bp_var, route_path) for each route decorator."""
    results = []
    for search_dir in [
        os.path.join(project_root, "backend", "routes"),
        os.path.join(project_root, "vidgenerator", "src", "routes"),
    ]:
        if not os.path.isdir(search_dir):
            continue
        for fname in sorted(os.listdir(search_dir)):
            if not fname.endswith(".py") or fname.startswith("_") or ".backup" in fname:
                continue
            path = os.path.join(search_dir, fname)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                for m in ROUTE_SIMPLE_PATTERN.finditer(content):
                    bp_var, route_path = m.group(1), m.group(2)
                    if route_path and not route_path.startswith("/static"):
                        results.append((bp_var, route_path))
            except Exception:
                pass
    return results
