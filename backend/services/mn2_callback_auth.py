"""Shared-secret auth for external casino/aggregator MN2 bet/win callbacks."""
from __future__ import annotations

import os
from flask import request


def callback_authorized() -> bool:
    secret = (os.environ.get("MN2_CALLBACK_SECRET") or os.environ.get("AGGREGATOR_CALLBACK_SECRET") or "").strip()
    if not secret:
        # Dev-only: allow when explicitly bypassed
        bypass = (os.environ.get("MN2_CALLBACK_BYPASS") or "").strip().lower() in ("1", "true", "yes")
        return bypass
    token = (
        request.headers.get("X-MN2-Callback-Token")
        or request.headers.get("X-Callback-Token")
        or request.args.get("token")
        or ""
    ).strip()
    body = request.get_json(silent=True) or {}
    if not token:
        token = (body.get("callback_token") or body.get("secret") or "").strip()
    return token == secret
