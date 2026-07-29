"""Marketplace user agents — tick all buyers (daemon loop)."""
from __future__ import annotations

import os
from typing import Any, Dict

from backend.services import agent_marketplace_service as mkt


def run_all_marketplace_agents_tick() -> Dict[str, Any]:
    udir = mkt._USER_AGENTS_DIR
    if not os.path.isdir(udir):
        return {"success": True, "skipped": True, "reason": "no_user_agents_dir", "users": 0, "ran": 0}

    user_ids = [name[:-5] for name in os.listdir(udir) if name.endswith(".json")]
    if not user_ids:
        return {"success": True, "skipped": True, "reason": "no_users", "users": 0, "ran": 0}

    total_ran = 0
    errors = 0
    for uid in user_ids:
        try:
            res = mkt.run_all_user_agents(uid)
            total_ran += int(res.get("ran") or 0)
        except Exception:
            errors += 1

    return {
        "success": errors == 0,
        "skipped": False,
        "users": len(user_ids),
        "ran": total_ran,
        "errors": errors,
    }
