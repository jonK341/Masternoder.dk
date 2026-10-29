"""API Lab — categorized, tryable catalog of live routes."""
from __future__ import annotations

import os
import re
from collections import defaultdict

from flask import Blueprint, Response, current_app, jsonify, request

api_lab_bp = Blueprint("api_lab", __name__)

_PARAM = re.compile(r"<(?:[^:>]+:)?([^>]+)>")

_ALIASES = {
    "agents": "agent",
    "users": "user",
    "wallets": "wallet",
    "errors": "error",
}

_PINNED = (
    "health",
    "mn2",
    "shop",
    "nft",
    "floor",
    "camgirls",
    "generator",
    "battle",
    "points",
    "hosting",
    "paypal",
    "discord",
)

_MIN_STANDALONE = 8

_LABELS = {
    "more": "More",
    "health": "Health",
    "version": "Version",
    "generator": "Video generator",
    "shop": "Shop",
    "mn2": "MN2 coin",
    "nft": "NFTs",
    "floor": "Studio floor",
    "camgirls": "Studio",
    "battle": "Battle",
    "points": "Points",
    "trophies": "Trophies",
    "user": "Users",
    "users": "Users",
    "paypal": "PayPal",
    "discord": "Discord",
    "agent": "Agents",
    "agents": "Agents",
    "debugger": "Debugger",
    "game": "Game",
    "gallery": "Gallery",
    "chat": "Chat",
    "social": "Social",
    "unified": "Unified",
    "monetization": "Monetization",
    "lab": "This lab",
    "star-map": "Star map",
    "profile": "Profile",
    "quests": "Quests",
    "casino": "Casino",
    "hosting": "Hosting",
    "wallet": "Wallets",
    "wallets": "Wallets",
    "exchange": "Exchange",
    "market": "Market",
    "podcast": "Podcast",
    "news": "News",
    "stats": "Stats",
    "analytics": "Analytics",
    "monitor": "Monitor",
    "error": "Errors",
    "errors": "Errors",
}


def category_for(path: str) -> str:
    """First meaningful segment under /api/ (or /vidgenerator/api/)."""
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


def build_catalog(rules) -> dict:
    """rules: iterable of objects with .rule and .methods, or (path, methods) tuples."""
    seen = set()
    endpoints = []
    for rule in rules:
        if isinstance(rule, tuple):
            path, methods = rule
        else:
            path = str(getattr(rule, "rule", ""))
            methods = getattr(rule, "methods", []) or []
        if not path or path.startswith("/static"):
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
    def _sort_key(key):
        pinned = _PINNED.index(key) if key in _PINNED else 99
        return (pinned, -counts[key], key)

    categories = [
        {"id": key, "label": label_for(key) if key != "more" else "More", "count": counts[key]}
        for key in sorted(counts, key=_sort_key)
    ]
    return {
        "success": True,
        "total": len(endpoints),
        "categories": categories,
        "endpoints": endpoints,
    }


def _page_path() -> str:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "vidgenerator", "api-lab", "index.html")


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
@api_lab_bp.route("/vidgenerator/api-lab", methods=["GET"])
@api_lab_bp.route("/vidgenerator/api-lab/", methods=["GET"])
def api_lab_page():
    return _serve_page()


@api_lab_bp.route("/api/lab/catalog", methods=["GET"])
@api_lab_bp.route("/vidgenerator/api/lab/catalog", methods=["GET"])
def api_lab_catalog():
    catalog = build_catalog(current_app.url_map.iter_rules())
    query = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    if query or category:
        rows = catalog["endpoints"]
        if category and category != "all":
            rows = [row for row in rows if row["category"] == category]
        if query:
            rows = [
                row
                for row in rows
                if query in row["path"].lower() or query in row["method"].lower() or query in row["category"]
            ]
        catalog = dict(catalog)
        catalog["endpoints"] = rows
        catalog["total"] = len(rows)
        catalog["filtered"] = True
    return jsonify(catalog), 200
