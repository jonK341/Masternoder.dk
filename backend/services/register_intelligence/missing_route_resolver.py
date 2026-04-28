"""
Missing Route Resolver - Ensures 404 errors are registered to the right places.
Integrates with auto_fix_endpoints and missing_endpoints_routes.
"""
import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class MissingRouteResolver:
    """
    Resolves 404 paths to correct registration.
    - Logs 404s for analysis
    - Suggests blueprint or missing_endpoints
    - Can generate route stubs for missing_endpoints
    """

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        self.logs_dir = os.path.join(self.project_root, "logs", "register_intelligence")
        os.makedirs(self.logs_dir, exist_ok=True)
        self._404_log = os.path.join(self.logs_dir, "404_occurrences.jsonl")
        self._resolutions_file = os.path.join(self.logs_dir, "suggested_resolutions.json")

    def normalize_path_for_comparison(self, path: str) -> str:
        """Normalize path for matching (strip /vidgenerator, etc)."""
        p = path.replace("/vidgenerator", "").split("?")[0]
        p = re.sub(r"/\d+", "/<id>", p)
        p = re.sub(r"/[a-f0-9-]{36}", "/<uuid>", p, flags=re.I)
        return p or "/"

    def log_404(self, path: str, method: str = "GET") -> Dict[str, Any]:
        """Log a 404 occurrence for later resolution."""
        entry = {
            "path": path,
            "method": method,
            "normalized": self.normalize_path_for_comparison(path),
            "ts": datetime.now().isoformat(),
        }
        try:
            with open(self._404_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
        return entry

    def get_404_patterns(self) -> Dict[str, Dict]:
        """Aggregate 404 patterns from log."""
        patterns = {}
        if not os.path.exists(self._404_log):
            return patterns
        try:
            with open(self._404_log, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        norm = entry.get("normalized", entry.get("path", ""))
                        if norm not in patterns:
                            patterns[norm] = {"count": 0, "examples": [], "methods": set()}
                        patterns[norm]["count"] += 1
                        patterns[norm]["methods"].add(entry.get("method", "GET"))
                        if entry["path"] not in patterns[norm]["examples"]:
                            patterns[norm]["examples"].append(entry["path"])
                            if len(patterns[norm]["examples"]) > 5:
                                patterns[norm]["examples"].pop(0)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        for k, v in patterns.items():
            v["methods"] = list(v["methods"])
        return patterns

    def generate_missing_endpoint_stub(self, path: str, method: str = "GET") -> str:
        """
        Generate a Python route stub for missing_endpoints_routes.py.
        Returns the code string to append (user must review before applying).
        """
        norm = self.normalize_path_for_comparison(path)
        path_api = path if "/api/" in path else "/api" + path.replace("/vidgenerator", "")
        path_vid = path_api if "/vidgenerator" in path_api else path_api.replace("/api/", "/vidgenerator/api/")
        stub = '''
@missing_endpoints_bp.route('%s', methods=['%s'])
@missing_endpoints_bp.route('%s', methods=['%s'])
def _auto_stub_%s():
    """Auto-generated stub - review and implement."""
    return jsonify({
        "success": True,
        "message": "Stub endpoint - implement in missing_endpoints_routes",
        "path": request.path,
        "method": request.method,
    }), 200
''' % (
            path_api, method.upper(),
            path_vid, method.upper(),
            re.sub(r"[^a-z0-9]", "_", norm.replace("/", "_")).strip("_")[:50] or "stub",
        )
        return stub
