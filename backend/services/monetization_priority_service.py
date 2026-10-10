"""
Queue priority for paid / subscribed users (#5).

Lower returned bonus = higher priority in video_job_queue (subtract from score).
"""
from __future__ import annotations

import os
from typing import Any, Dict


def queue_priority_bonus(user_id: str) -> int:
    """
    Negative-ish adjustment: return value to SUBTRACT from base queue score.
    Pro subscription → 45, VIP pass → 25, shop gen_priority booster → 50 (existing).
    """
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return 0
    bonus = 0
    try:
        from backend.services.monetization_subscription_service import list_bindings_for_user

        if list_bindings_for_user(uid):
            bonus = max(bonus, int(os.environ.get("MONETIZATION_PRO_QUEUE_BONUS", "45")))
    except Exception:
        pass
    try:
        from backend.services.shop_monetization_service import get_vip_status

        vip = get_vip_status(uid)
        if vip.get("active"):
            bonus = max(bonus, int(os.environ.get("MONETIZATION_VIP_QUEUE_BONUS", "25")))
    except Exception:
        pass
    try:
        from backend.services.monetization_config_service import get_default_tier_id
        from backend.services.monetization_tier_service import resolve_user_tier

        tier = resolve_user_tier(uid) or get_default_tier_id()
        if str(tier).lower() == "pro":
            bonus = max(bonus, 35)
    except Exception:
        pass
    return bonus


def priority_status(user_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "user_id": user_id,
        "queue_priority_bonus": queue_priority_bonus(user_id),
        "note": "Higher bonus = sooner encode when VIDEO_JOB_QUEUE is enabled.",
    }
