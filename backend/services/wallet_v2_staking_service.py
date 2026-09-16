"""Wallet v2 staking tab — pool snapshot + block trophy grants."""
from __future__ import annotations

from typing import Any, Dict


def build_wallet_staking(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid in ("default_user", "guest"):
        return {
            "success": True,
            "guest": True,
            "message": "Sign in to view staking and trophy rewards.",
        }

    out: Dict[str, Any] = {
        "success": True,
        "user_id": uid,
        "guest": False,
        "platform_trophy_rewards": True,
        "on_chain_mint": False,
    }

    try:
        from backend.services.mn2_staking_service import get_stake, get_staking_leaderboard

        out["stake"] = get_stake(uid)
        out["leaderboard"] = get_staking_leaderboard(limit=5)
    except Exception:
        out["estimate"] = None
        out["leaderboard"] = None

    try:
        from backend.services.mn2_staking_service import get_rewards_table

        out["rewards"] = get_rewards_table(uid, limit=10)
    except Exception:
        out["rewards"] = None

    try:
        from backend.services.staking_trophy_reward_service import user_staking_trophy_grants

        out["trophy_grants"] = user_staking_trophy_grants(uid, limit=10)
    except Exception:
        out["trophy_grants"] = {"grants": [], "count": 0}

    try:
        from backend.services.wallet_upgrades_service import get_progress

        prog = get_progress(uid)
        unlocked = set(prog.get("unlocked_ids") or [])
        out["upgrade"] = {
            "id": "WR-UPG-251",
            "unlocked": "WR-UPG-251" in unlocked,
            "label": "Staking trophy drops",
            "description": "Interval winners receive block smiley trophies in your wallet.",
        }
    except Exception:
        out["upgrade"] = None

    out["links"] = {
        "trophies_tab": "/wallets?tab=trophies",
        "block_gallery": "/shop?tab=block-gallery",
        "staking_monitor": "/staking-monitor",
        "profile_staking": "/profile#profile-mn2-wallet-card",
    }
    return out
