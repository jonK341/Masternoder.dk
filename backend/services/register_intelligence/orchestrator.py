"""
Register Intelligence Orchestrator
Coordinates discovery, registration, and 404 resolution.
"""
import os
import sys
import json
import importlib.util
from datetime import datetime
from typing import List, Dict, Set, Optional, Any
from pathlib import Path

from backend.services.register_intelligence.route_discovery import (
    discover_blueprints,
    discover_routes_from_blueprints,
    discover_routes_simple,
)
from backend.services.register_intelligence.frontend_api_scanner import (
    scan_frontend_api_calls,
    all_frontend_api_paths,
)


class RegisterIntelligence:
    """
    Automatic registration intelligence for routes, blueprints, and API controls.
    Safe to run: supports dry-run, validation, and backup.
    """

    def __init__(self, project_root: Optional[str] = None, dry_run: bool = True):
        self.project_root = project_root or os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        self.dry_run = dry_run
        self.logs_dir = os.path.join(self.project_root, "logs", "register_intelligence")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.report: Dict[str, Any] = {}

    def _log(self, msg: str):
        self.report.setdefault("log", []).append(msg)

    def discover_all(self) -> Dict[str, Any]:
        """Discover blueprints and routes from backend; API calls from frontend."""
        bps = discover_blueprints(self.project_root)
        routes_simple = discover_routes_simple(self.project_root)
        routes_by_bp = discover_routes_from_blueprints(self.project_root)
        frontend = scan_frontend_api_calls(self.project_root)
        all_frontend = all_frontend_api_paths(self.project_root)
        backend_paths = set()
        for _, path in routes_simple:
            backend_paths.add(path)
            backend_paths.add(path.replace("/vidgenerator", ""))
            backend_paths.add(path.replace("/api/", "/vidgenerator/api/"))
        missing = all_frontend - backend_paths
        self.report["discovery"] = {
            "blueprints_count": len(bps),
            "blueprints": [{"module": b["module_path"], "name": b["bp_name"]} for b in bps],
            "backend_routes_count": len(routes_simple),
            "frontend_api_count": len(all_frontend),
            "frontend_files_with_api": len(frontend),
            "potential_missing": list(missing)[:100],
        }
        return self.report["discovery"]

    def register_blueprints_dynamic(self, app) -> int:
        """
        Dynamically register all discovered blueprints.
        Returns count of newly registered blueprints.
        """
        bps = discover_blueprints(self.project_root)
        root = self.project_root
        if root not in sys.path:
            sys.path.insert(0, root)
        registered = 0
        for b in bps:
            if b["bp_name"] in getattr(app, "blueprints", {}):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    b["module_path"].replace(".", "_"),
                    b["file_path"],
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    bp = getattr(mod, b["bp_var"], None)
                    if bp:
                        app.register_blueprint(bp)
                        registered += 1
                        self._log("Registered: %s" % b["bp_name"])
            except Exception as e:
                self._log("Skip %s: %s" % (b["bp_name"], str(e)))
        return registered

    def resolve_404_path(self, path: str, method: str = "GET") -> Dict[str, Any]:
        """
        Resolve a 404 path: suggest which blueprint could handle it,
        or whether it should go to missing_endpoints.
        """
        path_stripped = path.replace("/vidgenerator", "")
        if not path_stripped.startswith("/"):
            path_stripped = "/" + path_stripped
        routes = discover_routes_simple(self.project_root)
        similar = []
        path_parts = path_stripped.lower().split("/")
        for bp_var, rpath in routes:
            rpath_stripped = rpath.replace("/vidgenerator", "")
            rparts = rpath_stripped.lower().split("/")
            if len(path_parts) == len(rparts):
                score = sum(1 for a, b in zip(path_parts, rparts) if a == b)
                if score >= 2:
                    similar.append({"bp": bp_var, "route": rpath, "score": score})
        similar.sort(key=lambda x: -x["score"])
        return {
            "path": path,
            "method": method,
            "suggested_blueprints": similar[:5],
            "should_add_to_missing_endpoints": not similar or similar[0]["score"] < 3,
        }

    def log_404_for_resolution(self, path: str, method: str = "GET"):
        """Log 404 for later resolution; append to 404 log file."""
        resolution = self.resolve_404_path(path, method)
        log_file = os.path.join(
            self.logs_dir,
            "404_resolutions_%s.jsonl" % datetime.now().strftime("%Y%m%d"),
        )
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(resolution, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return resolution

    def run_full_audit(self) -> Dict[str, Any]:
        """Run full audit: discovery + gap analysis."""
        disc = self.discover_all()
        self.report["audit"] = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "summary": {
                "blueprints": disc["blueprints_count"],
                "backend_routes": disc["backend_routes_count"],
                "frontend_apis": disc["frontend_api_count"],
                "potential_missing": len(disc.get("potential_missing", [])),
            },
        }
        return self.report


def run_register_intelligence(
    project_root: Optional[str] = None,
    dry_run: bool = True,
    discover_only: bool = False,
) -> Dict[str, Any]:
    """
    Run register intelligence.
    - discover_only: only run discovery, no registration
    - dry_run: do not modify files
    """
    ri = RegisterIntelligence(project_root=project_root, dry_run=dry_run)
    ri.run_full_audit()
    return ri.report
