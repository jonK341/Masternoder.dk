"""Unified MN2 reward path for game, battle, quests, and starmap."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.activity_events_service import emit


def credit_mn2(
    user_id: str,
    amount: float,
    *,
    source: str,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not user_id or user_id in ("default_user", "anon", "anonymous"):
        return {"success": False, "error": "authenticated_user_required"}
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}

    meta = dict(metadata or {})
    meta["reference"] = reference
    meta["source"] = source

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    result = unified_points_db.add_points(
        user_id, "mn2_balance", amt, source=source, metadata=meta,
    )
    if not result.get("success"):
        return result
    if result.get("duplicate"):
        return result

    append_entry(
        user_id=user_id,
        entry_type=source,
        amount=amt,
        txid=reference,
        metadata=meta,
    )
    emit(
        "game_mn2_reward",
        user_id=user_id,
        channel="game",
        text=f"+{amt} MN2 ({source})",
        payload={"amount": amt, "source": source, "reference": reference},
    )
    return {"success": True, "amount": amt, "user_id": user_id, "source": source}
