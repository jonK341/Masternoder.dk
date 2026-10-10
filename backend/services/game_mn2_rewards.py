"""Unified MN2 reward path for game, battle, quests, and starmap."""
from __future__ import annotations

from typing import Any, Dict, Optional


def credit_mn2(
    user_id: str,
    amount: float,
    *,
    source: str,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from backend.services.micro_tx_hooks import credit_mn2_reward

    return credit_mn2_reward(
        user_id,
        float(amount or 0),
        source=source,
        reason=source,
        idempotency_key=reference,
        reference=reference,
        metadata=metadata,
    )
