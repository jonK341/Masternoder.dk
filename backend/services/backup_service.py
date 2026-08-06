"""Scheduled backup of MN2-critical stores (Gate S)."""
from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BACKUP_ROOT = os.path.join(_BASE, "backups", "mn2")

# (source relative to project root, destination relative to backup dir)
_SOURCES: Tuple[Tuple[str, str], ...] = (
    ("data/mn2_ledger.json", "data/mn2_ledger.json"),
    ("data/mn2_config.json", "data/mn2_config.json"),
    ("data/treasury_signoff.json", "data/treasury_signoff.json"),
    ("logs/unified_points", "logs/unified_points"),
    ("instance/database.db", "instance/database.db"),
)


def run_backup(*, label: Optional[str] = None) -> Dict[str, Any]:
    """Copy critical MN2/economy files into backups/mn2/<timestamp>/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = os.path.join(_BACKUP_ROOT, label or ts)
    os.makedirs(backup_dir, exist_ok=True)
    copied: List[str] = []
    skipped: List[str] = []

    for src_rel, dst_rel in _SOURCES:
        src = os.path.join(_BASE, src_rel)
        dst = os.path.join(backup_dir, dst_rel)
        if not os.path.exists(src):
            skipped.append(src_rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
        else:
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        copied.append(src_rel)

    manifest = {
        "ts": ts,
        "backup_dir": backup_dir,
        "copied": copied,
        "skipped": skipped,
    }
    manifest_path = os.path.join(backup_dir, "manifest.json")
    import json
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    try:
        from backend.services.admin_audit_service import log_action
        log_action("mn2_backup", actor="backup_service", payload={"copied": copied, "backup_dir": backup_dir})
    except Exception:
        pass

    return {"success": True, "backup_dir": backup_dir, "copied": copied, "skipped": skipped}
