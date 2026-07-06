"""Shared owner/admin auth for exchange and profit-daemon control routes.

Single source of truth for the shared-secret check used by Business Control,
the profit daemon monitor (owner view), and the laptop control app.

Security notes:
- The key is accepted from headers only (X-Exchange-Admin-Key / X-Admin-Key).
  Query-string keys are rejected because they leak into access logs, browser
  history, and Referer headers.
- Comparison uses hmac.compare_digest to avoid timing side channels.
- If no admin key is configured in the environment, everything is denied.
"""
from __future__ import annotations

import hmac
import os

from flask import request

ADMIN_KEY_HEADER = "X-Exchange-Admin-Key"
ADMIN_KEY_HEADER_ALT = "X-Admin-Key"


def configured_admin_key() -> str:
    return (
        os.environ.get("EXCHANGE_ADMIN_KEY")
        or os.environ.get("COGS_ADMIN_REPORT_KEY")
        or ""
    ).strip()


def admin_authorized() -> bool:
    secret = configured_admin_key()
    if not secret:
        return False
    got = (
        request.headers.get(ADMIN_KEY_HEADER)
        or request.headers.get(ADMIN_KEY_HEADER_ALT)
        or ""
    ).strip()
    return bool(got) and hmac.compare_digest(got, secret)
