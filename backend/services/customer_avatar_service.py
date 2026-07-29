"""Deterministic customer avatars — off-request backfill for Stage 3 security cron."""
from __future__ import annotations

import hashlib
import os
from typing import Any, Dict, List

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CUSTOMERS_DIR = os.path.join(_BASE, "static", "img", "customers")
_POINTS_DIR = os.path.join(_BASE, "logs", "unified_points")


def _avatar_path(user_id: str) -> str:
    safe = (user_id or "").strip()
    return os.path.join(_CUSTOMERS_DIR, f"{safe}.svg")


def svg_for_user(user_id: str) -> str:
    """Build a small deterministic avatar SVG (no network)."""
    uid = (user_id or "user").strip() or "user"
    digest = hashlib.sha256(uid.encode("utf-8")).hexdigest()
    c1 = f"#{digest[0:6]}"
    c2 = f"#{digest[6:12]}"
    c3 = f"#{digest[12:18]}"
    initial = uid[:1].upper()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="{initial}">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="64" height="64" rx="32" fill="url(#g)"/>'
        f'<circle cx="32" cy="26" r="12" fill="{c3}" opacity="0.85"/>'
        f'<rect x="14" y="40" width="36" height="18" rx="9" fill="{c3}" opacity="0.7"/>'
        f'<text x="32" y="34" text-anchor="middle" font-size="14" font-family="sans-serif" fill="#fff">{initial}</text>'
        f"</svg>"
    )


def ensure_avatar(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    path = _avatar_path(uid)
    if os.path.isfile(path):
        return {"success": True, "user_id": uid, "created": False, "path": path}
    os.makedirs(_CUSTOMERS_DIR, exist_ok=True)
    svg = svg_for_user(uid)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(svg)
    os.replace(tmp, path)
    return {"success": True, "user_id": uid, "created": True, "path": path}


def backfill_missing_avatars(*, limit: int = 40) -> Dict[str, Any]:
    """Generate missing customer avatars from unified_points directory."""
    safe_limit = max(1, min(int(limit or 40), 200))
    if not os.path.isdir(_POINTS_DIR):
        return {"success": True, "scanned": 0, "created": 0, "skipped": 0, "results": []}

    created = 0
    skipped = 0
    results: List[Dict[str, Any]] = []
    names = sorted(n for n in os.listdir(_POINTS_DIR) if n.endswith(".json"))[: safe_limit * 3]
    for name in names:
        if created >= safe_limit:
            break
        uid = name[:-5]
        if not uid or uid.startswith("pool_"):
            continue
        path = _avatar_path(uid)
        if os.path.isfile(path):
            skipped += 1
            continue
        row = ensure_avatar(uid)
        results.append(row)
        if row.get("created"):
            created += 1

    return {
        "success": True,
        "scanned": len(names),
        "created": created,
        "skipped": skipped,
        "results": results[:20],
    }
