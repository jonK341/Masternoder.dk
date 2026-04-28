"""
Frontend API Scanner - Extracts API paths from JS/HTML.
"""
import os
import re
from typing import List, Set, Dict
from pathlib import Path

# Patterns for frontend API calls
FETCH_URL_PATTERN = re.compile(
    r"(?:fetch\s*\(\s*|['\"])"
    r"((?:https?://[^\s'\"]+|/vidgenerator/api/[^\s'\"]+|/api/[^\s'\"]+|[`$]\{.*?API_BASE.*?\}/[^\s'`\"]+))"
)
API_PATH_PATTERN = re.compile(
    r"(?:/vidgenerator/api|/api)/([a-zA-Z0-9/_\-\{\$\.]+)"
)
TEMPLATE_VAR_PATTERN = re.compile(
    r"`\$\{(?:API_BASE|BASE_URL|MASTER_DASHBOARD_API_BASE)[^}]*\}([^`]+)`"
)
STRING_API_PATTERN = re.compile(
    r"['\"](/vidgenerator/api/[^'\"]+|/api/[^'\"]+)['\"]"
)
BACKEND_CONNECTOR_PATTERN = re.compile(
    r"(?:endpoint|url|path)\s*:\s*['\"](/vidgenerator/api/[^'\"]+|/api/[^'\"]+)['\"]"
)


def _normalize_path(path: str) -> str:
    """Convert path to canonical form (strip query, replace template vars)."""
    path = path.split("?")[0]
    path = re.sub(r'\$\{[^}]+\}', '<id>', path)
    path = re.sub(r'/<[^>]+>', '/<id>', path)
    return path.rstrip("/") or "/"


def scan_frontend_api_calls(project_root: str) -> Dict[str, Set[str]]:
    """
    Scan vidgenerator/ and backend/templates for API calls.
    Returns {source_file: set(normalized_api_paths)}.
    """
    results: Dict[str, Set[str]] = {}
    search_roots = [
        os.path.join(project_root, "vidgenerator"),
        os.path.join(project_root, "backend", "templates"),
    ]
    ext = (".js", ".html", ".htm")
    for root in search_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if not any(fname.endswith(e) for e in ext):
                    continue
                path = os.path.join(dirpath, fname)
                rel = os.path.relpath(path, project_root)
                paths = set()
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    # String literals
                    for m in STRING_API_PATTERN.finditer(content):
                        p = _normalize_path(m.group(1))
                        if p and ("/api/" in p or "/vidgenerator/api/" in p):
                            paths.add(p)
                    # Template literals (API_BASE + path)
                    for m in TEMPLATE_VAR_PATTERN.finditer(content):
                        p = _normalize_path(m.group(1))
                        if p:
                            paths.add("/vidgenerator/api" + p if not p.startswith("/") else p)
                    # fetch(url)
                    for m in FETCH_URL_PATTERN.finditer(content):
                        url = m.group(1)
                        if "/api/" in url or "/vidgenerator/api/" in url:
                            if url.startswith("http") or url.startswith("/"):
                                p = _normalize_path(
                                    url.split("?")[0].replace(
                                        "https://", ""
                                    ).split("/", 3)[-1] if "://" in url else url
                                )
                                if p:
                                    paths.add(p if p.startswith("/") else "/" + p)
                    # backend connector style
                    for m in BACKEND_CONNECTOR_PATTERN.finditer(content):
                        paths.add(_normalize_path(m.group(1)))
                except Exception:
                    pass
                if paths:
                    results[rel] = paths
    return results


def all_frontend_api_paths(project_root: str) -> Set[str]:
    """Aggregate all unique API paths from frontend."""
    by_file = scan_frontend_api_calls(project_root)
    out = set()
    for paths in by_file.values():
        out.update(paths)
    return out
