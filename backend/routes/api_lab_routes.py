"""API Lab — categorized, tryable catalog of live /api routes."""
from __future__ import annotations

import os
import re
import time
from collections import defaultdict

from flask import Blueprint, Response, current_app, jsonify, request

api_lab_bp = Blueprint("api_lab", __name__)

_CACHE = {"built_at": 0.0, "catalog": None}
_CACHE_TTL_SECS = 30.0

_PARAM = re.compile(r"<(?:[^:>]+:)?([^>]+)>")

# Normalize noisy / typo first segments into one category id.
_ALIASES = {
    "agents": "agent",
    "users": "user",
    "wallets": "wallet",
    "errors": "error",
    "trophie": "trophies",
    "debug": "debugger",
    "debugging": "debugger",
    "aggregators": "aggregator",
    "stats": "analytics",
    "game-hub": "game",
    "quests": "game",
    "starmap25": "star-map",
    "profit": "profit-daemon",
    "ai-agents": "ai",
    "agent-tech": "agent",
    "customers": "customer",
    "ptc": "ads",
    "auth": "user",
    "profiler": "profile",
    "system-skills": "agent",
    "create-app": "lab",
    "documentary": "generator",
    "advanced-calculator": "points",
    "point-calculator": "points",
    "atomic-calculator": "points",
    "shop-v3": "shop",
    "floor": "camgirls",
    "hosting": "mn2",
}

# Product / ops categories always shown as their own group (even if small).
_PINNED = (
    "health",
    "mn2",
    "shop",
    "nft",
    "camgirls",
    "generator",
    "battle",
    "points",
    "paypal",
    "discord",
    "casino",
    "exchange",
    "market",
    "agent",
    "user",
    "game",
    "social",
    "podcast",
    "monetization",
    "star-map",
    "trophies",
    "gallery",
    "chat",
    "news",
    "lab",
)

# Fold into "more" unless pinned — raised so tiny stubs do not litter the sidebar.
_MIN_STANDALONE = 10

# Internal / tooling categories sit under Other by default in the UI.
_INTERNAL = frozenset({
    "debugger",
    "error",
    "monitor",
    "monitoring",
    "ops",
    "admin",
    "more",
})

_LABELS = {
    "more": "Other",
    "health": "Health",
    "version": "Version",
    "generator": "Video generator",
    "shop": "Shop",
    "mn2": "MN2 coin",
    "nft": "NFTs",
    "camgirls": "Studio",
    "battle": "Battle",
    "points": "Points",
    "trophies": "Trophies",
    "user": "Users",
    "paypal": "PayPal",
    "discord": "Discord",
    "agent": "Agents",
    "debugger": "Debugger",
    "game": "Game",
    "gallery": "Gallery",
    "chat": "Chat",
    "social": "Social",
    "monetization": "Monetization",
    "lab": "Lab",
    "star-map": "Star map",
    "profile": "Profile",
    "casino": "Casino",
    "wallet": "Wallets",
    "exchange": "Exchange",
    "market": "Market",
    "podcast": "Podcast",
    "news": "News",
    "analytics": "Analytics",
    "monitor": "Monitor",
    "monitoring": "Monitoring",
    "error": "Errors",
    "aggregator": "Aggregator",
    "compendium": "Compendium",
    "ai": "AI",
    "profit-daemon": "Profit daemon",
    "customer": "Customers",
    "ads": "Ads / PTC",
    "leaderboard": "Leaderboard",
    "rulebooks": "Rulebooks",
}


def category_for(path: str) -> str:
    """First meaningful segment under /api/ (or legacy /vidgenerator/api/)."""
    raw = path or "/"
    for prefix in ("/vidgenerator/api/", "/api/"):
        if raw.startswith(prefix):
            rest = raw[len(prefix):].strip("/")
            head = rest.split("/", 1)[0] if rest else "root"
            return head or "root"
    if raw.startswith("/vidgenerator/"):
        rest = raw[len("/vidgenerator/"):].strip("/")
        return (rest.split("/", 1)[0] if rest else "pages") or "pages"
    rest = raw.strip("/")
    return (rest.split("/", 1)[0] if rest else "root") or "root"


def label_for(category: str) -> str:
    if category in _LABELS:
        return _LABELS[category]
    return category.replace("-", " ").replace("_", " ").title()


def path_params(path: str) -> list:
    return _PARAM.findall(path or "")


def is_try_safe(method: str, path: str) -> bool:
    return method == "GET" and "<" not in (path or "")


def normalize_category(category: str) -> str:
    return _ALIASES.get(category, category)


def is_catalog_path(path: str) -> bool:
    """Keep real JSON API routes; drop pages, catch-alls, and lab HTML aliases."""
    if not path:
        return False
    if path.startswith("/static"):
        return False
    if path in ("/api", "/api/"):
        return False
    # Must be under /api/ (not /api-lab) or the legacy API prefix.
    if path.startswith("/api/"):
        pass
    elif path.startswith("/vidgenerator/api/"):
        pass
    else:
        return False
    # Drop Flask catch-all redirects and file servers.
    if "<path:" in path:
        return False
    if path.endswith("/index.html"):
        return False
    return True


def build_catalog(rules) -> dict:
    """rules: iterable of objects with .rule and .methods, or (path, methods) tuples."""
    seen = set()
    endpoints = []
    dropped = 0
    for rule in rules:
        if isinstance(rule, tuple):
            path, methods = rule
        else:
            path = str(getattr(rule, "rule", ""))
            methods = getattr(rule, "methods", []) or []
        if not is_catalog_path(path):
            if path and not path.startswith("/static"):
                dropped += 1
            continue
        for method in methods:
            method = str(method).upper()
            if method in ("HEAD", "OPTIONS"):
                continue
            key = (method, path)
            if key in seen:
                continue
            seen.add(key)
            category = normalize_category(category_for(path))
            endpoints.append(
                {
                    "method": method,
                    "path": path,
                    "category": category,
                    "params": path_params(path),
                    "try_safe": is_try_safe(method, path),
                }
            )
    endpoints.sort(key=lambda row: (row["category"], row["path"], row["method"]))
    counts = defaultdict(int)
    for row in endpoints:
        counts[row["category"]] += 1
    for row in endpoints:
        cat = row["category"]
        if cat not in _PINNED and counts[cat] < _MIN_STANDALONE:
            row["category"] = "more"
    counts = defaultdict(int)
    for row in endpoints:
        counts[row["category"]] += 1
        row["internal"] = row["category"] in _INTERNAL

    def _sort_key(key):
        if key == "more":
            return (2, 0, key)
        if key in _INTERNAL:
            return (1, -counts[key], key)
        pinned = _PINNED.index(key) if key in _PINNED else 50
        return (0, pinned, -counts[key], key)

    categories = []
    for key in sorted(counts, key=_sort_key):
        categories.append(
            {
                "id": key,
                "label": label_for(key),
                "count": counts[key],
                "internal": key in _INTERNAL,
            }
        )
    try_safe = sum(1 for row in endpoints if row["try_safe"])
    return {
        "success": True,
        "total": len(endpoints),
        "try_safe": try_safe,
        "dropped": dropped,
        "categories": categories,
        "endpoints": endpoints,
    }


def _page_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "api-lab", "index.html")


def _serve_page():
    path = _page_path()
    if not os.path.isfile(path):
        return Response("API Lab page missing", status=500, mimetype="text/plain")
    with open(path, encoding="utf-8") as handle:
        html = handle.read()
    response = Response(html, mimetype="text/html; charset=utf-8")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@api_lab_bp.route("/api-lab", methods=["GET"])
@api_lab_bp.route("/api-lab/", methods=["GET"])
def api_lab_page():
    return _serve_page()


def _cached_catalog(rules=None):
    now = time.monotonic()
    cached = _CACHE.get("catalog")
    if cached is not None and (now - float(_CACHE.get("built_at") or 0)) < _CACHE_TTL_SECS:
        return cached
    catalog = build_catalog(rules if rules is not None else current_app.url_map.iter_rules())
    _CACHE["catalog"] = catalog
    _CACHE["built_at"] = now
    return catalog


def catalog_response(rules=None):
    """Build the JSON body for GET /api/lab/catalog (shared with fallbacks)."""
    catalog = dict(_cached_catalog(rules))
    query = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    include_internal = (request.args.get("internal") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "all",
    )
    if not include_internal:
        rows = [row for row in catalog["endpoints"] if not row.get("internal")]
        cats = [cat for cat in catalog["categories"] if not cat.get("internal")]
        catalog["endpoints"] = rows
        catalog["categories"] = cats
        catalog["total"] = len(rows)
        catalog["try_safe"] = sum(1 for row in rows if row["try_safe"])
        catalog["internal_hidden"] = True
    if query or category:
        rows = catalog["endpoints"]
        if category and category != "all":
            rows = [row for row in rows if row["category"] == category]
        if query:
            rows = [
                row
                for row in rows
                if query in row["path"].lower()
                or query in row["method"].lower()
                or query in row["category"]
            ]
        catalog["endpoints"] = rows
        catalog["total"] = len(rows)
        catalog["filtered"] = True
    return catalog


@api_lab_bp.route("/api/lab/catalog", methods=["GET"])
def api_lab_catalog():
    return jsonify(catalog_response()), 200
