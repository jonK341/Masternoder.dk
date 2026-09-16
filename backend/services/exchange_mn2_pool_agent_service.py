"""Dedicated MN2/USDT/USDC pool controller agent."""
from __future__ import annotations

from typing import Any, Dict

from backend.services.exchange_mn2_pool_service import (
    mn2_pool_status,
    pool_agent_id,
    run_mn2_pool_agent_tick,
)


def tick(*, force: bool = False) -> Dict[str, Any]:
    result = run_mn2_pool_agent_tick(force=force)
    result["agent_id"] = pool_agent_id()
    result["strategy"] = "mn2_pool"
    return result


def agent_status() -> Dict[str, Any]:
    st = mn2_pool_status()
    return {
        "success": True,
        "agent_id": pool_agent_id(),
        "strategy": "mn2_pool",
        "enabled": st.get("enabled"),
        "pool_assets": st.get("pool_assets"),
        "pool_gaps": st.get("pool_gaps"),
        "last_tick_at": st.get("last_tick_at"),
        "tick_count": st.get("tick_count"),
    }
