"""Shared paths for profit daemon heartbeat and state files."""
from __future__ import annotations

import os

from backend.services import crypto_exchange_service as ex


def project_root() -> str:
    for key in ("MASTER_ROOT", "APP_ROOT", "PROJECT_ROOT"):
        val = os.environ.get(key, "").strip()
        if val:
            return os.path.abspath(val)
    return ex._BASE


def heartbeat_path() -> str:
    explicit = os.environ.get("PROFIT_DAEMON_HEARTBEAT_PATH", "").strip()
    if explicit:
        return os.path.abspath(explicit)
    return os.path.join(project_root(), "logs", "daemon_all_profit_heartbeat.json")
