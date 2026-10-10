"""
Explorer hub feature flags (P4 #188 / #189).

EXPLORER_HUB_V2 — master switch (default on).
EXPLORER_HUB_V2_CANARY_PERCENT — 0–100; when <100, only that share of clients get v2.
"""
import hashlib
import os
from typing import Optional


def _truthy(val: Optional[str], default: bool = True) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() not in ("0", "false", "no", "off")


def hub_v2_master_enabled() -> bool:
    return _truthy(os.environ.get("EXPLORER_HUB_V2"), default=True)


def hub_v2_canary_percent() -> int:
    try:
        return max(0, min(100, int(os.environ.get("EXPLORER_HUB_V2_CANARY_PERCENT", "100") or 100)))
    except (TypeError, ValueError):
        return 100


def hub_v2_enabled_for_client(client_key: Optional[str] = None) -> bool:
    """Return whether the crypto hub v2 UI should be served for this client."""
    if not hub_v2_master_enabled():
        return False
    pct = hub_v2_canary_percent()
    if pct >= 100:
        return True
    if pct <= 0:
        return False
    key = (client_key or "anonymous").strip() or "anonymous"
    bucket = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % 100
    return bucket < pct
