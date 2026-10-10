"""Shared admin check for debug, debugger, and error-read APIs.

Accepts a configured admin secret via header, bearer token, query key, or a
session flag set by POST /api/debugger/unlock. When no secret is configured
the endpoints stay closed (401) so they are not world-readable.
"""
from __future__ import annotations

import os
from typing import Iterable, Optional

from flask import Blueprint, jsonify, request, session

_ENV_KEYS = ("COGS_ADMIN_REPORT_KEY", "EXCHANGE_ADMIN_KEY", "DEBUGGER_ADMIN_KEY")
_HEADER_NAMES = ("X-Admin-Key", "X-Cogs-Admin-Key", "X-Exchange-Admin-Key")
_SESSION_FLAG = "debugger_admin"


def configured_admin_secrets() -> list:
    secrets = []
    for name in _ENV_KEYS:
        value = (os.environ.get(name) or "").strip()
        if value and value not in secrets:
            secrets.append(value)
    return secrets


def _supplied_secrets() -> list:
    supplied = []
    for header in _HEADER_NAMES:
        supplied.append((request.headers.get(header) or "").strip())
    supplied.append((request.args.get("admin_key") or "").strip())
    supplied.append((request.args.get("key") or "").strip())
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        supplied.append(auth[7:].strip())
    body = request.get_json(silent=True) or {}
    if isinstance(body, dict):
        supplied.append(str(body.get("admin_key") or body.get("key") or "").strip())
    return [item for item in supplied if item]


def admin_authorized() -> bool:
    if session.get(_SESSION_FLAG):
        return True
    expected = configured_admin_secrets()
    if not expected:
        return False
    return any(item in expected for item in _supplied_secrets())


def grant_admin_session(secret: str) -> bool:
    expected = configured_admin_secrets()
    if not expected or (secret or "").strip() not in expected:
        return False
    session[_SESSION_FLAG] = True
    session.permanent = True
    return True


def admin_required_response():
    """Return a JSON denial, or None when the caller is an admin."""
    if admin_authorized():
        return None
    return jsonify({
        "success": False,
        "error": "admin_required",
        "code": "admin_required",
        "message": "Admin authentication is required",
    }), 401


def protect_blueprint(
    bp: Blueprint,
    *,
    methods: Optional[Iterable[str]] = None,
    skip_paths: Optional[Iterable[str]] = None,
    skip_endpoint_suffixes: Optional[Iterable[str]] = None,
) -> None:
    """Attach a before_request admin gate to a blueprint."""
    allowed = {m.upper() for m in methods} if methods else None
    skipped = set(skip_paths or ())
    suffixes = tuple(skip_endpoint_suffixes or ())

    def _gate():
        if request.path in skipped:
            return None
        if allowed and request.method not in allowed:
            return None
        endpoint = request.endpoint or ""
        if suffixes and endpoint.endswith(suffixes):
            return None
        return admin_required_response()

    _gate.__name__ = f"admin_gate_{bp.name}"
    bp.before_request(_gate)
