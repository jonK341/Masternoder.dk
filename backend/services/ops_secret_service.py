"""Shared ops/admin secret resolution for gated API routes."""
from __future__ import annotations

import os
from typing import Optional


def ops_secret() -> str:
    """Return the active ops secret from environment (first match wins)."""
    for key in ("YOUR_OPS_SECRET", "DISCORD_OPS_SECRET", "ADMIN_OPS_SECRET"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return ""


def ops_auth_ok(header_value: Optional[str], *, remote_addr: str = "") -> bool:
    """True when header matches configured ops secret, or localhost with no secret."""
    secret = ops_secret()
    if not secret:
        return remote_addr in ("127.0.0.1", "::1")
    return (header_value or "").strip() == secret
