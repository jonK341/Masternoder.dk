"""Backup critical money JSON stores (Gate S DR)."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BACKUP_ROOT = os.path.join(_BASE, "backups", "mn2")


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_backup() -> Dict[str, Any]:
    stamp = _iso()
    dest = os.path.join(_BACKUP_ROOT, stamp)
    os.makedirs(dest, exist_ok=True)
    copied: List[str] = []

    singles = [
        ("data/mn2_ledger.json", "mn2_ledger.json"),
        ("data/mn2_user_addresses.json", "mn2_user_addresses.json"),
        ("data/agent_wallets.json", "agent_wallets.json"),
        ("data/agent_treasury.json", "agent_treasury.json"),
    ]
    for rel, name in singles:
        src = os.path.join(_BASE, rel.replace("/", os.sep))
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(dest, name))
            copied.append(name)

    up_src = os.path.join(_BASE, "logs", "unified_points")
    if os.path.isdir(up_src):
        up_dest = os.path.join(dest, "unified_points")
        shutil.copytree(up_src, up_dest, dirs_exist_ok=True)
        copied.append("unified_points/")

    manifest = {"ts": stamp, "copied": copied}
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return {"success": True, "backup_dir": dest, "copied": copied}
