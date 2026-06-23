"""Shared owner/ops authentication for cockpit-gated surfaces.

Portal consolidation (2026-06): admin/ops HTML surfaces gate on this module;
unauthenticated visitors redirect to /owner#… anchors. See owner_panel_routes.py.
"""
from __future__ import annotations

import os
from typing import Optional

from flask import redirect, request, session

SESSION_KEY = "owner_ops_authenticated"


def ops_secret() -> str:
    return (
        os.environ.get("OWNER_PANEL_SECRET")
        or os.environ.get("DISCORD_OPS_SECRET")
        or os.environ.get("ADMIN_OPS_SECRET")
        or ""
    ).strip()


def localhost_ok() -> bool:
    return request.environ.get("REMOTE_ADDR") in ("127.0.0.1", "::1")


def secret_matches(provided: str) -> bool:
    secret = ops_secret()
    if not secret:
        return localhost_ok()
    return bool(provided) and provided == secret


def ops_ok() -> bool:
    if session.get(SESSION_KEY):
        return True
    hdr = (request.headers.get("X-Ops-Secret") or "").strip()
    if hdr and secret_matches(hdr):
        return True
    if not ops_secret():
        return localhost_ok()
    return False


def owner_redirect(anchor: str = ""):
    """Redirect unauthenticated users to Owner Cockpit (optional hash anchor)."""
    target = f"/owner#{anchor}" if anchor else "/owner"
    return redirect(target, code=302)


def require_ops_redirect(anchor: str = "") -> Optional[object]:
    """Return a redirect response when not authenticated, else None."""
    if ops_ok():
        return None
    return owner_redirect(anchor)
